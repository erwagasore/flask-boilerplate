FROM python:3.8-rc-alpine
ENV ROOT /foo
WORKDIR $ROOT
COPY setup.py .
RUN pip install -e .
COPY . .
EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]
