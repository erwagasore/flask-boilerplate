FROM python:3.7-alpine
ENV ROOT /api
WORKDIR $ROOT
COPY setup.py .
RUN apk update && \
    apk add postgresql-libs && \
    apk add --virtual .build-deps gcc musl-dev postgresql-dev libffi-dev && \
    pip install -e . && \
    apk --purge del .build-deps
RUN pip install -e .
COPY . .
EXPOSE 6000
CMD ["flask" "run" "--host=0.0.0.0" "--port=6000"]
