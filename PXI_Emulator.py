# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 22:01:55 2014

@author: Nate
"""

import httplib, mimetypes, numpy, time, pdb
import msgpack, msgpack_numpy
msgpack_numpy.patch()

def send_compile_request(shotnumber=22):
    post_multipart("127.0.0.1:8083",'127.0.0.1:8083'
                    ,[('IDLSocket_ResponseFunction','compile_active_xtsm')
                    ,('shotnumber',str(shotnumber)),('Labview Version','1.0')
                    ,('data_context','default:127.0.0.1'),('terminator','die')],[])

def post_multipart(host, selector, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    content_type, body = encode_multipart_formdata(fields, files)
    h = httplib.HTTP(host)
    h.putrequest('POST', selector)
    h.putheader('content-type', content_type)
    h.putheader('content-length', str(len(body)))
    h.endheaders()
    h.send(body)
    h.close()
    #errcode, errmsg, headers = h.getreply()
    return #h.file.read()

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\n\r'
    L = []
    L.append('--' + BOUNDARY )
    for (key, value) in fields:
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
        L.append('--' + BOUNDARY + '--')
    #L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    
def post_databomb(shotnumber=1):
    """
    Post a fictitious databomb of random data
    """
    msgdict={"sender":"PXI1Slot3/ai0:3","shotnumber":str(int(shotnumber)),"repnumber":-1}
    msgdict.update({"somedata":numpy.random.random(10000)})
    msg=msgpack.packb(msgdict)
    post_multipart("127.0.0.1:8083",'127.0.0.1:8083'
                    ,[('IDLSocket_ResponseFunction','databomb')
                    ,('databomb',msg),('terminator','die')],[])
    
def constant_run(delay=2,iter=100):
    shotnumber = 0    
    for a in range(iter):
        send_compile_request(shotnumber)
        time.sleep(delay)
        #post_databomb(shotnumber)
        shotnumber+=1