FROM python:3.6

WORKDIR /app

# install donkey with tensorflow (cpu only version)
ADD ./setup.py /app/setup.py
ADD ./README.md /app/README.md
RUN pip install -e .[tf]

# get testing requirements
RUN pip install -e .[dev]

# setup jupyter notebook to run without password
RUN pip install jupyter notebook
RUN jupyter notebook --generate-config
RUN echo "c.NotebookApp.password = ''">>/root/.jupyter/jupyter_notebook_config.py
RUN echo "c.NotebookApp.token = ''">>/root/.jupyter/jupyter_notebook_config.py

# add the whole app dir after install so the pip install isn't updated when code changes.
ADD . /app

#start the jupyter notebook
CMD jupyter notebook --no-browser --ip 0.0.0.0 --port 8888 --allow-root  --notebook-dir=/app/notebooks

#port for donkeycar
EXPOSE 8887

#port for jupyter notebook
EXPOSE 8888