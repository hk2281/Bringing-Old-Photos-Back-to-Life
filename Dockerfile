FROM ubuntu:20.04

RUN apt update && DEBIAN_FRONTEND=noninteractive apt install git bzip2 wget unzip python3-pip python3-dev cmake libgl1-mesa-dev python-is-python3 libgtk2.0-dev -yq
ADD . /app
WORKDIR /app

RUN cd Face_Enhancement/models/networks/ &&\
  git clone https://github.com/vacancy/Synchronized-BatchNorm-PyTorch &&\
  cp -rf Synchronized-BatchNorm-PyTorch/sync_batchnorm . &&\
  cd ../../../

RUN cd Global/detection_models &&\
  git clone https://github.com/vacancy/Synchronized-BatchNorm-PyTorch &&\
  cp -rf Synchronized-BatchNorm-PyTorch/sync_batchnorm . &&\
  cd ../../



RUN cd Face_Detection/ &&\
  wget https://huggingface.co/hk2281/dlib/resolve/main/shape_predictor_68_face_landmarks.dat.bz2 &&\
  bzip2 -d shape_predictor_68_face_landmarks.dat.bz2 &&\
  cd ../ 

RUN cd Face_Enhancement/ &&\
  wget https://huggingface.co/hk2281/dlib/resolve/main/F_Echeckpoints.zip -O checkpoints.zip &&\
  unzip checkpoints.zip &&\
  cd ../ &&\
  cd Global/ &&\
  wget https://huggingface.co/hk2281/dlib/resolve/main/Gl_checkpoints.zip?download=true -O checkpoints.zip &&\
  unzip checkpoints.zip &&\
  rm -f checkpoints.zip &&\
  cd ../


RUN python3 -m venv venv
ENV PATH="/app/venv/bin:$PATH"

RUN pip3 install numpy

RUN pip3 install dlib

RUN pip3 install -r r.txt

RUN git clone https://github.com/NVlabs/SPADE.git

RUN cd SPADE/ && pip3 install -r requirements.txt

RUN cd ..

CMD ["uvicorn", "src.app:app", "--workers", "4", "--host", "0.0.0.0", "--port", "8000"]
