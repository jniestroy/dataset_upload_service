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
def homepage():

    #if more metadata is required add to metadata.html in templates
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

            ################################################
            #Here is where post to ORS takes place
            #################################################
            req = requests.put("http://uvadcos.io/id/UVA/",json = result,verify = False)

            #########################
            #If created redirect to dataset upload page
            # below id is newly minted id from mongo
            ##########################
            if req.json().get('created'):

                full_id = req.json()['created']['@id']

                _,_,base,namespace,name,id = full_id.split('/')

                return redirect("http://localhost:5001/upload/"+ name + '/'+ id,code = 302)

            #Only time mine failed to post was if test namespace wasnt made
            else:
                return("Make Test Namespace")

        return "Error metadata did not meet requirements.\nError: " + valid['error']
      #return render_template("result.html",result = result)



#Upload Object to MINio endpoint
#ID is passed in from previous page
#upload.html displays minted id if id was created
#and allows user to post dataset to minio with accociated metadata
@app.route('/upload/<name>/<id>')
def upload_file(name,id):
    return render_template('upload.html',id = id,name = name)

#################################
#In service below no addition is made to id in mongo
#need to add update to id for datadownload
#after object is posted in minio
#################################

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

        #Minio requires size of file to grab it
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)

        try:
               minioClient.put_object('testbucket', f.filename, f,size,metadata = meta)

        except ResponseError as err:
               return 'There was an error posting to Minio'
        #f.save(secure_filename(f.filename))

        return 'file uploaded successfully'

if __name__ == '__main__':
   app.run(host='0.0.0.0',port = 5005)
