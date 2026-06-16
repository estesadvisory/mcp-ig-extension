# Official AWS Lambda base image for Python 3.11.
# Generic images like python:*-slim produce manifests that Lambda rejects.
# The base image includes the Lambda Runtime Interface Client (LAMBDA_TASK_ROOT = /var/task).

FROM public.ecr.aws/lambda/python:3.11

COPY pyproject.toml ${LAMBDA_TASK_ROOT}/
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY config/ ${LAMBDA_TASK_ROOT}/config/

RUN pip install --no-cache-dir ${LAMBDA_TASK_ROOT}/

# Handler module lives at /var/task/src/handler.py after install copies are resolved.
# setuptools installs modules into site-packages; keep source for config path resolution.
ENV CONFIG_PATH=/var/task/config/accounts.json

CMD ["handler.handler"]