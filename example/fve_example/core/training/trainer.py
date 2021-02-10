import logging
import numpy as np
import pyaml

from bdb import BdbQuit
from os.path import join
from pathlib import Path
from tqdm.auto import tqdm

from chainer.backends import cuda
from chainer.dataset import convert
from chainer.serializers import save_npz
from chainer.training import Trainer as DefaultTrainer
from chainer.training import extensions

from chainer_addons.training import lr_shift
from chainer_addons.training import optimizer

from cvdatasets.utils import attr_dict
from cvdatasets.utils import new_iterator

from fve_example.core.training.extensions import FeatureStatistics
from fve_example.core.training.updater import get_updater


class Trainer(DefaultTrainer):
	default_intervals = attr_dict(
		print =		(1,  'epoch'),
		log =		(1,  'epoch'),
		eval =		(1,  'epoch'),
		analyze =	(1,  'epoch'),
		# analyze =	(2,  'iteration'),
		snapshot =	(10, 'epoch'),
	)

	@classmethod
	def new(cls, args, target, train_it, val_it=None, **kwargs):

		with open(Path(args.output, "args.yml"), "w") as out:
			pyaml.dump(args.__dict__, out)

		opt_kwargs = {}
		if args.optimizer == "rmsprop":
			opt_kwargs["alpha"] = 0.9

		opt = optimizer(args.optimizer,
			model=target,
			lr=args.learning_rate,
			decay=args.decay,
			gradient_clipping=False,
			**opt_kwargs)


		if args.only_clf:
			target.disable_update()
			target.model.clf_layer.enable_update()
			if target.separate_model is not None:
				target.separate_model.clf_layer.enable_update()

		updater_cls, updater_kwargs = get_updater(args)

		updater = updater_cls(
			iterator=train_it,
			optimizer=opt,
			**updater_kwargs
		)

		if val_it is None:
			evaluator = None

		else:
			evaluator = extensions.Evaluator(
				iterator=val_it,
				target=target,
				device=updater.device,
				progress_bar=True
			)
			evaluator.default_name = "val"


		analyzer = None
		if args.analyze_features:
			_train_it, _ = new_iterator(train_it.dataset,
				n_jobs=args.n_jobs,
				batch_size=args.batch_size,
				repeat=False, shuffle=False)

			analyzer = FeatureStatistics(target, _train_it, val_it,
				device=updater.device)

		return cls(args,
			updater=updater,
			evaluator=evaluator,
			analyzer=analyzer,
			**kwargs)


	def __init__(self, args, updater, evaluator=None, analyzer=None, intervals=default_intervals):

		outdir = args.output
		logging.info("Training outputs are saved under \"{}\"".format(outdir))


		super(Trainer, self).__init__(
			updater=updater,
			stop_trigger=(args.epochs, 'epoch'),
			out=outdir
		)

		self.evaluator = evaluator
		if evaluator is not None:
			self.extend(evaluator, trigger=intervals.eval)

		self.analyzer = analyzer
		if analyzer is not None:
			self.extend(analyzer, trigger=intervals.analyze)

		opt = updater.get_optimizer("main")
		lr_shift_ext = lr_shift(opt,
			init=args.learning_rate,
			rate=args.lr_decrease_rate, target=args.lr_target)
		self.extend(lr_shift_ext, trigger=(args.lr_shift, 'epoch'))

		self.extend(extensions.observe_lr(), trigger=intervals.log)
		self.extend(extensions.LogReport(trigger=intervals.log))

		ext = extensions.ExponentialShift(
			attr="aux_lambda",
			init=args.aux_lambda,
			rate=args.aux_lambda_rate,
			optimizer=self.clf)
		self.extend(ext, trigger=(args.lr_shift, 'epoch'))
		logging.info(f"Aux impact starts at {args.aux_lambda} "
			f"and is reduced by {args.aux_lambda_rate} "
			f"every {args.lr_shift} epoch")

		### Snapshotting ###
		self.setup_snapshots(args, self.clf, intervals.snapshot,
			fmt="ft_clf_epoch{0.updater.epoch:03d}.npz")

		### Reports and Plots ###
		print_values, plot_values = self.reportables(args)
		self.extend(extensions.PrintReport(print_values), trigger=intervals.print)
		for name, values in plot_values.items():
			ext = extensions.PlotReport(values, 'epoch', file_name='{}.png'.format(name))
			self.extend(ext)

		### Progress bar ###
		if not args.no_progress:
			self.extend(extensions.ProgressBar(update_interval=1))

	def setup_snapshots(self, args, obj, trigger, fmt):
		self._no_snapshot = args.no_snapshot
		if self._no_snapshot:
			logging.warning("Models are not snapshot!")
		else:
			self.extend(extensions.snapshot_object(obj, fmt), trigger=trigger)
			logging.info("Snapshot format: \"{}\"".format(fmt))

	def eval_name(self, name):
		if self.evaluator is None:
			return name

		return f"{self.evaluator.default_name}/{name}"

	def reportables(self, args):

		print_values = [
			"elapsed_time",
			"epoch",
			# "lr",

			"main/accu", self.eval_name("main/accu"),
			# "main/f1", self.eval_name("main/f1"),
			"main/loss", self.eval_name("main/loss"),

		]

		plot_values = {
			"accuracy": [
				"main/accu",  self.eval_name("main/accu"),
			],
			"loss": [
				"main/loss", self.eval_name("main/loss"),
			],
		}

		if args.parts != "GLOBAL":
			print_values.extend([
				"main/g_accu", self.eval_name("main/g_accu"),
				# "main/g_loss", self.eval_name("main/g_loss"),
			])

			print_values.extend([
				"main/p_accu", self.eval_name("main/p_accu"),
				# "main/p_loss", self.eval_name("main/p_loss"),
			])

			if args.aux_lambda > 0:

				print_values.extend([
					# "main/aux_p_accu", self.eval_name("main/aux_p_accu"),
					# "main/aux_p_loss", self.eval_name("main/aux_p_loss"),
				])

			if args.fve_type != "no":
				print_values.extend([
					"main/dist", self.eval_name("main/dist")
				])

		return print_values, plot_values

	@property
	def clf(self):
		return self.updater.get_optimizer("main").target

	@property
	def model(self):
		return self.clf.model


	def run(self):

		logging.info("Snapshotting is {}abled".format("dis" if self._no_snapshot else "en"))

		def dump(suffix):
			if self._no_snapshot:
				return

			save_npz(join(self.out,
				"clf_{}.npz".format(suffix)), self.clf)
			# save_npz(join(self.out,
			# 	"model_{}.npz".format(suffix)), self.model)

		try:
			super(Trainer, self).run()
		except (KeyboardInterrupt, BdbQuit) as e:
			raise e
		except Exception as e:
			dump("exception")
			raise e
		else:
			dump("final")