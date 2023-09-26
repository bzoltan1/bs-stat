FROM opensuse/bci/python:3.11
WORKDIR /app
ENV VIRTUAL_ENV=/app/venv
RUN zypper in -y python311-dbm && python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt bs-stat.py ./
RUN source $VIRTUAL_ENV/bin/activate && pip3 install -r requirements.txt
CMD source $VIRTUAL_ENV/bin/activate && python3 /app/bs-stat.py

