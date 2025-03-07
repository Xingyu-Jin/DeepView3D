#!/usr/bin/env bash
#SBATCH -N 1	  # nodes requested
#SBATCH -n 1	  # tasks requested
#SBATCH --partition=Standard
#SBATCH --gres=gpu:1
#SBATCH --mem=12000  # memory in Mb
#SBATCH --time=0-8:00:00
#SBATCH --exclude=landonia23

export STUDENT_ID=$(whoami)




# Finetune ShapeHD 3D estimator with GAN losses

outdir=./output/shapehd
rm -rf $outdir

marrnet2=./downloads/models/marrnet2.pt
gan=/path/to/gan.pt

if [ $# -lt 2 ]; then
    echo "Usage: $0 gpu class[ ...]"
    exit 1
fi
gpu="$1"
class="$2"
shift # shift the remaining arguments
shift

set -e


source /home/${STUDENT_ID}/miniconda3/bin/activate shaperecon

python train.py \
    --net shapehd \
    --marrnet2 "$marrnet2" \
    --gan "$gan" \
    --dataset shapenet \
    --classes "$class" \
    --canon_sup \
    --w_gan_loss 1e-3 \
    --batch_size 4 \
    --epoch_batches 1000 \
    --eval_batches 10 \
    --optim adam \
    --lr 1e-3 \
    --epoch 1000 \
    --vis_batches_vali 10 \
    --gpu "$gpu" \
    --save_net 1 \
    --workers 4 \
    --logdir "$outdir" \
    --suffix '{classes}_w_ganloss{w_gan_loss}' \
    --tensorboard \
    $*

source /home/${STUDENT_ID}/miniconda3/bin/deactivate shaperecon
