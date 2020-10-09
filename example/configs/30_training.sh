
if [[ -z ${DATASET} ]]; then
	echo "DATASET variable is not set!"
	exit 1
fi

GPU=${GPU:-0}
BATCH_SIZE=${BATCH_SIZE:-8}
UPDATE_SIZE=${UPDATE_SIZE:-64}
LABEL_SMOOTHING=${LABEL_SMOOTHING:-0.1}
OPTIMIZER=${OPTIMIZER:-rmsprop}
EPOCHS=${EPOCHS:-60}
DEBUG=${DEBUG:-0}


if [[ ${DEBUG} != 0 ]]; then
	OPTS="${OPTS} --debug"
fi

# >>> LR definition >>>
INIT_LR=${INIT_LR:-1e-4}
LR_DECAY=${LR_DECAY:-1e-1}
LR_STEP=${LR_STEP:-20}
LR_TARGET=${LR_TARGET:-1e-6}

LR=${LR:-"-lr ${INIT_LR} -lrd ${LR_DECAY} -lrs ${LR_STEP} -lrt ${LR_TARGET}"}
# >>>>>>>>>>>>>>>>>>>>>
OUTPUT=${OUTPUT:-".results/${DATASET}/${OPTIMIZER}/$(date +%Y-%m-%d-%H.%M.%S.%N)"}

OPTS="${OPTS} --gpu ${GPU}"
OPTS="${OPTS} --batch_size ${BATCH_SIZE}"
OPTS="${OPTS} --update_size ${UPDATE_SIZE}"
OPTS="${OPTS} --label_smoothing ${LABEL_SMOOTHING}"
OPTS="${OPTS} --optimizer ${OPTIMIZER}"
OPTS="${OPTS} --epochs ${EPOCHS}"
OPTS="${OPTS} --output ${OUTPUT}"
OPTS="${OPTS} ${LR}"