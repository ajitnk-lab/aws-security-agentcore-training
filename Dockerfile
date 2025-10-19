FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY security-agent-app.py .

CMD ["security-agent-app.handler"]
