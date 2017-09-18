FROM ubuntu

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    python3 \
    python3-numpy \
    python3-pip \
    python3-dev \
    enchant \
    poppler-utils \
    libxml2-dev libxslt1-dev antiword \
    unrtf tesseract-ocr libjpeg-dev

RUN pip3 install --upgrade pip

RUN pip3 install -U setuptools

RUN pip3 install tensorflow

RUN pip3 install keras

RUN pip3 install gensim

RUN pip3 install jupyter

RUN pip3 install pandas

RUN pip3 install matplotlib

RUN pip3 install cython

RUN pip3 install -U spacy

RUN python3 -m spacy download en

RUN pip3 install -U scikit-learn

RUN pip3 install wordsegment

RUN pip3 install pyenchant

# Install local version that installs
#RUN pip3 install git+https://github.com/deanmalmgren/textract.git

RUN apt-get install tesseract-ocr

RUN pip3 install feedparser

RUN pip3 install python-docx

#RUN pip3 install patentdata>=0.0.7

ENV INSTALL_PATH /patentdata
RUN mkdir -p $INSTALL_PATH
WORKDIR $INSTALL_PATH

COPY . .
RUN pip install --editable .

RUN python3 -m nltk.downloader punkt && python3 -m nltk.downloader stopwords \
    && python3 -m nltk.downloader averaged_perceptron_tagger \
    && python3 -m nltk.downloader wordnet

EXPOSE 8888

# Add a notebook profile.
RUN mkdir -p -m 700 /root/.jupyter/ && \
    echo "c.NotebookApp.ip = '*'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.password = u'sha1:dcdb6e651f8c:609a36df6ee9005f50b9e0e9d79590d108053f03'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.token = ''" >> /root/.jupyter/jupyter_notebook_config.py

#ENTRYPOINT ["tini", "--"]
CMD ["jupyter", "notebook", "--no-browser", "--allow-root"]
