from flask import Flask, render_template, request, redirect
import requests
import json
from werkzeug.datastructures import ImmutableMultiDict
from minio import Minio
from minio.error import (ResponseError, BucketAlreadyOwnedByYou,BucketAlreadyExists)
import os

app = Flask(__name__)

minio_name = os.environ['MINIO_DOCKER_NAME']
minio_key = os.environ['MINIO_ACCESS_KEY']
minio_secret = os.environ["MINIO_SECRET_KEY"]


@app.route('/')
def student():
    return("hi")
    return render_template('metadata.html')

@app.route('/post-object',methods = ['POST', 'GET'])
def result():
    if request.method == 'POST':
        #2 options for metadata uploading
        #first user can type in second user can input json file
        if not request.files:
            result = request.form
            result.to_dict(flat=True)

        else:
            f = request.files['file']
            result = f.read()
            try:
                result=json.loads(result)
            except:
                return("Error parsing given file. Please post a json file.")

        #With given metadata validate using service
        req = requests.post(url = "http://validator:5000/validatejson",json = result)
        valid = req.json()

        #if valid metadata post identifer on ors
        if valid['valid']:

            req = requests.put("https://ors:8080/uid/test/",json = result,verify = False)

            if req.json().get('created'):
                full_id = req.json()['created']['@id']
                _,_,base,namespace,name,id = full_id.split('/')
                return redirect("http://localhost:5001/upload/"+ name + '/'+ id,code = 302)
            else:
                return("Make Test Namespace")
        return "Error metadata did not meet requirements.\nError: " + valid['error']
      #return render_template("result.html",result = result)

#Upload Object to MINio endpoint
@app.route('/upload/<name>/<id>')
def upload_file(name,id):
    return render_template('upload.html',id = id,name = name)

#Endpoint that posts object to MINio
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file2():
    if request.method == 'POST':
        meta = request.form.to_dict(flat=True)
        f = request.files['file']
        minioClient = Minio(minio_name,
            access_key=minio_key,
            secret_key=minio_secret,
            secure=False)
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)
        try:
               minioClient.put_object('testbucket', f.filename, f,size,metadata = meta)
        except ResponseError as err:
               return 'There was an error'
        #f.save(secure_filename(f.filename))
        return 'file uploaded successfully'

if __name__ == '__main__':
   app.run(host='0.0.0.0',port = 5005)
