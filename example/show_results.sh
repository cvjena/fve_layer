#!/usr/bin/env bash

MODEL_TYPES=${MODEL_TYPES:-"chainercv2.resnet50 cvmodelz.InceptionV3"}
FVE_TYPES=${FVE_TYPES:-"no em grad"}

FOLDER=$1

if [[ -z $FOLDER ]]; then
	echo "FOLDER was not set! Please set it as 1 argument for the script!"
	exit 1;
fi
if [[ ! -d $FOLDER ]]; then
	echo "$FOLDER is not a directory"
	exit 1;
fi

METRIC=${2:-val/main/accu}

for mt in $MODEL_TYPES; do
	for fve in $FVE_TYPES; do
		echo "=== FVE: ${fve} | Model: ${mt} ==="
		for f in ${FOLDER}/*/meta/args.yml; do
			if grep -q "fve_type: ${fve}" $f && grep -q "model_type: ${mt}" $f;
			then
				grep $METRIC $(dirname $(dirname $f))/log  | tail -n1;
			fi
		done
	done
done

