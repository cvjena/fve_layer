import logging
import numpy as np
import pyaml

from bdb import BdbQuit
from pathlib import Path
from tqdm.auto import tqdm

from chainer.backends import cuda
from chainer.dataset import convert
from chainer.serializers import save_npz
from chainer.training import extensions
from chainer_addons.training import lr_shift
from chainer_addons.training import optimizer
from cvdatasets.utils import attr_dict
from cvdatasets.utils import new_iterator
from cvfinetune.training import Trainer as DefaultTrainer

from fve_example.core.training.extensions import FeatureStatistics
from fve_example.core.training.updater import updater_params

def trainer_params(opts) -> dict:
	return dict(trainer_cls=Trainer)


class Trainer(DefaultTrainer):

	def __init__(self, opts, *args, **kwargs):
		super().__init__(opts=opts, *args, **kwargs)

		ext = extensions.ExponentialShift(
			attr="aux_lambda",
			init=opts.aux_lambda,
			rate=opts.aux_lambda_rate,
			optimizer=self.clf)

		self.extend(ext, trigger=(opts.lr_shift, 'epoch'))
		logging.info(f"Aux impact starts at {opts.aux_lambda} "
			f"and is reduced by {opts.aux_lambda_rate} "
			f"every {opts.lr_shift} epoch")

	def reportables(self, args):

		print_values = [
			"elapsed_time",
			"epoch",
			# "lr",

			"main/accu", self.eval_name("main/accu"),
			"main/accu2", self.eval_name("main/accu2"),
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
			])

			print_values.extend([
				"main/p_accu", self.eval_name("main/p_accu"),
			])

			if args.aux_lambda > 0:

				print_values.extend([
					"main/aux_p_accu", self.eval_name("main/aux_p_accu"),
				])

		return print_values, plot_values
