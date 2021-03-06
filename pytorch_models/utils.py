import json
import subprocess
import uuid
import boto3
import os
import time

from pytorch_lightning.callbacks import Callback

def save_json(x, out_path):
    with open(out_path, 'w') as out_file:
        json.dump(x, out_file)

def s3_sync(from_uri, to_uri):
    cmd = ['aws', 's3', 'sync', from_uri, to_uri]
    print(f'Syncing from {from_uri} to {to_uri}...')
    subprocess.run(cmd)

def batch_submit(command, attempts=3):
    job_def = os.environ['JOB_DEF']
    job_queue = os.environ['JOB_QUEUE']
    client = boto3.client('batch')
    job_name = 'pytorch-models-{}'.format(uuid.uuid4())

    kwargs = {
        'jobName': job_name,
        'jobQueue': job_queue,
        'jobDefinition': job_def,
        'containerOverrides': {
            'command': command
        },
        'retryStrategy': {
            'attempts': attempts
        }
    }

    job_id = client.submit_job(**kwargs)['jobId']
    msg = 'submitted job with jobName={} and jobId={}'.format(
        job_name, job_id)
    print(command)
    print(msg)
    return job_id

class S3SyncCallback(Callback):
    def __init__(self, from_uri, to_uri, min_interval=60):
        super().__init__()
        self.from_uri = from_uri
        self.to_uri = to_uri
        self.min_interval = min_interval

        self.last_sync = time.time()

    def on_epoch_end(self, trainer, pl_module):
        elapsed = time.time() - self.last_sync
        if elapsed > self.min_interval:
            s3_sync(self.from_uri, self.to_uri)
            self.last_sync = time.time()
