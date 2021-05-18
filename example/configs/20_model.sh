
GPU=${GPU:-0}

# MODEL_TYPE=${MODEL_TYPE:-chainercv2.resnet50}
MODEL_TYPE=${MODEL_TYPE:-cvmodelz.InceptionV3}
PRE_TRAINING=${PRE_TRAINING:-imagenet}
PREPARE_TYPE=${PREPARE_TYPE:-model}

INPUT_SIZE=${INPUT_SIZE:-299}
PARTS_INPUT_SIZE=${PARTS_INPUT_SIZE:-299}

# concat mean
FEATURE_AGG=${FEATURE_AGG:-concat}

case $MODEL_TYPE in
	"cvmodelz.InceptionV3" | "chainercv2.inceptionv3" )
		PARTS_INPUT_SIZE=299
		PRE_TRAINING=inat
		if [[ ${BIG:-0} == 0 ]]; then
			INPUT_SIZE=299
		elif [[ ${BIG:-0} == -1 ]]; then
			INPUT_SIZE=107
			PARTS_INPUT_SIZE=107
		else
			INPUT_SIZE=427
		fi
		;;
	"cvmodelz.ResNet50" | "chainercv2.resnet50" )
		PARTS_INPUT_SIZE=224
		if [[ ${BIG:-0} == 0 ]]; then
			INPUT_SIZE=224
		else
			INPUT_SIZE=448
		fi
		;;
	"chainercv2.efficientnet" )
		PARTS_INPUT_SIZE=380
		INPUT_SIZE=380
		;;
esac


LOAD=${LOAD:-""}
WEIGHTS=${WEIGHTS:-""}

if [[ ! -z ${LOAD} ]]; then
	if [[ ! -z ${WEIGHTS} ]]; then
		echo "Set either LOAD or WEIGHTS!"
		exit 1

	else
		OPTS="${OPTS} --load ${LOAD}"
	fi

elif [[ ! -z ${WEIGHTS} ]]; then
	if [[ ! -z ${LOAD} ]]; then
		echo "Set either LOAD or WEIGHTS!"
		exit 1

	else
		OPTS="${OPTS} --weights ${WEIGHTS}"
	fi
fi

OPTS="${OPTS} --gpu ${GPU}"
OPTS="${OPTS} --model_type ${MODEL_TYPE}"
OPTS="${OPTS} --prepare_type ${PREPARE_TYPE}"
OPTS="${OPTS} --pre_training ${PRE_TRAINING}"
OPTS="${OPTS} --input_size ${INPUT_SIZE}"
OPTS="${OPTS} --parts_input_size ${PARTS_INPUT_SIZE}"
OPTS="${OPTS} --feature_aggregation ${FEATURE_AGG}"
OPTS="${OPTS} --load_strict"
