#!/usr/bin/env bash

#SBATCH -N 1	  # nodes requested
#SBATCH -n 1	  # tasks requested
#SBATCH --partition=LongJobs
#SBATCH --gres=gpu:1
#SBATCH --mem=12000  # memory in Mb
#SBATCH --time=0-72:00:00
export CUDA_HOME=/opt/cuda-9.0.176.1/

export CUDNN_HOME=/opt/cuDNN-7.0/

export STUDENT_ID=$(whoami)

export LD_LIBRARY_PATH=${CUDNN_HOME}/lib64:${CUDA_HOME}/lib64:$LD_LIBRARY_PATH

export LIBRARY_PATH=${CUDNN_HOME}/lib64:$LIBRARY_PATH

export CPATH=${CUDNN_HOME}/include:$CPATH

export PATH=${CUDA_HOME}/bin:${PATH}

export PYTHON_PATH=$PATH

mkdir -p /disk/scratch/${STUDENT_ID}


export TMPDIR=/disk/scratch/${STUDENT_ID}/
export TMP=/disk/scratch/${STUDENT_ID}/

mkdir -p ${TMP}/datasets/
export DATASET_DIR=${TMP}/datasets/


outdir=./output/marrnet2_2img_add

source /home/s1841522/miniconda3/bin/activate shaperecon
python train.py \
    --net marrnet2_2img_add \
    --dataset shapenet \
    --classes "chair" \
    --canon_sup \
    --batch_size 4 \
    --epoch_batches 2500 \
    --eval_batches 5 \
    --optim adam \
    --lr 1e-3 \
    --epoch 300 \
    --vis_batches_vali 10 \
    --gpu "-1" \
    --save_net 10 \
    --workers 10 \
    --logdir "$outdir" \
    --suffix '{classes}_canon-{canon_sup}'\
    --tensorboard\
    --resume -1
source /home/s1841522/miniconda3/bin/deactivate
