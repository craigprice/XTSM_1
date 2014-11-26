;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;This procedure opens a TCP/IP port 8082, and listens for a post.  The POST data is extracted, and a response is returned.
;POST form data should use the enctype='text/plain'.
;This shows transfer speed of 0.5MB/s without base64 decoding, and similar with
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
function listen_and_respond, response_function=rf, VERBOSE=vb, TIME=vbt
  readdelay=0.001
  T0=systime(1)
  T0=systime(1)
  ; find/allocate some free file units
  get_lun, unit1
  get_lun, unit2
  ; connect these to a port (:8082), listening, and a file unit to extract and put data on
  socket, unit1, 8082, /listen
  socket, unit2, accept=unit1
  ;the wait is necessary to head off 'blocking errors' - do not understand what these are
;  if (readdelay ne 0) then wait, readdelay
   test=1
   while ( test ) do test=NOT file_poll_input(unit2) 
  data=''
  array = ''
  line = ''
  flag=0
  T1=systime(1)
  WHILE NOT flag DO BEGIN
;    if (readdelay ne 0) then wait, readdelay
    test=1
    while ( test ) do test=NOT file_poll_input(unit2) 
    READF, unit2, line 
    array = [array, line] 
  ;  a blank line separates the header from data
    if (line eq '') then flag=1
  ;  if this is the content-length line, extract the number of characters therein
    if( (r=strsplit(line,'Content-Length:',Count=c,/REGEX,/FOLD_CASE)) and (c eq 1)) then cl=fix(strmid(line,r))
  ;  if this is the content-type line, extract it
    if( (r=strsplit(line,'Content-Type:',Count=c,/REGEX,/FOLD_CASE)) and (c eq 1)) then begin
      ct=STRUPCASE(STRTRIM((strsplit(line,'Content-Type:',/REGEX,/EXTRACT,/FOLD_CASE))[0],2))
      endif
  ENDWHILE
  if (strpos(strjoin(array),"stop_listening") ne -1) then begin 
      printf, unit2, '<b><span style="color:red;">IDLsocket terminated.</style></b>'
      free_lun, unit1
      free_lun, unit2
      return, 0
    endif
  ;print out header data
  if keyword_set(vb) then print, 'header data:'
  if keyword_set(vb) then print, array
  T2=systime(1)
  ; now extract data, keeping track of character count, end when content-length reached
  contentlength=0
  ; create a null variable named data to hold post data - use version-specific method
  if (fix((strsplit(!version.release,"\.",/regex,/extract))[0]) eq 8) then data=!null else data=''
;  if (not keyword_set(cl)) then cl = 10000000.
  while (contentlength lt cl) do begin
    ;if (readdelay ne 0) then wait, readdelay
    ;READF, unit2, line
    test=1
    while ( test ) do test=NOT file_poll_input(unit2) 
    READF, unit2, line 
    if (ct eq 'APPLICATION/X-WWW-FORM-URLENCODED') then data=[data,strsplit(line,'&',/regex,/extract)] else data=[data,line]
    contentlength+=strlen(line)
    if (stregex(line,'terminator',/boolean,/fold_case) ) then break
  endwhile
  if (fix((strsplit(!version.release,"\.",/regex,/extract))[0]) ne 8) then data=data[1:*]
  T3=systime(1)
  ;this next line converts values from base64 representation to decoded strings if we are using application/x-www-form-urlencoded
  if (ct eq 'APPLICATION/X-WWW-FORM-URLENCODED') then for j=0,((size(data))[1]-1) do begin
    equalconvert=strjoin(strsplit(strmid(data[j],strpos(data[j],'=')+1,strlen(data[j])-strpos(data[j],'=')),'\%3D',/regex,/extract,/preserve_null  ),'=')
    plusconvert=strjoin(strsplit(strmid(equalconvert,strpos(equalconvert,'+')+1,strlen(equalconvert)-strpos(equalconvert,'+')),'\%2B',/regex,/extract,/preserve_null  ),'+')
    data[j]=strmid(data[j],0,strpos(data[j],'=')+1)+string(idl_base64(plusconvert))
    endfor
  ; if there is a response function defined on the first line, note it, and remove it from data
  if (stregex(data[0],'IDLSocket_ResponseFunction=',/boolean,/fold_case)) then begin
    rf=(strsplit(data[0],'IDLSocket_ResponseFunction=',/regex,/extract))[0]
    data=data[1:*]
  endif
  if keyword_set(rf) then if (rf eq 'terminate_listen') then return, 0
  data=strjoin(data,string(10b))
  if keyword_set(vb) then print, 'POST data:'
  if keyword_set(vb) then print, data
  T4=systime(1)
  
  ;err=execute((strsplit(data,'=',/regex,/extract))[1])
  
  ; return a web-page to the socket stream
;  resp='<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8" /><title>Untitled Document</title></head><body>'
;  resp+=data+'</body></html>'
;  printf, unit2, resp

  if keyword_set(rf) then printf, unit2, call_function(rf, data, unit2) else printf, unit2, data
  T5=systime(1)
  
;  printf, unit2, 'Access-Control-Allow-Origin: http://localhost:8082'+String([10b,10b])
;  printf, unit2, '<html><body><p>hithere</p></body></html>'
  ; free the file streams
  free_lun, unit1
  free_lun, unit2
  T6=systime(1)
  if keyword_set(vbt) then begin
    TT=[T0,[T2,T3,T4,T5,T6]-T1]
    TTlabel=["time request received","header load","content load","content base64 conversion","responsefunction execution","freeing socket"]
    for j=0,5 do print, TTlabel[j], TT[j]
  endif
  return, 1
end

function XTSM_parse_from_socket, data, outputLUN
  ;print, 'parse from socket'
    data=strsplit(data,string(10b),/regex,/extract)
    ;remove the terminator line
    data=data[0:-2]
    ;remove the assignment part of the statement
    data[0]=strjoin((strsplit(data[0],'=',/regex,/extract))[1:*],'=')
    ;rejoin the strings
    data=strjoin(data,string(10b))
  return, 'this came from parse from socket'+string(10b)+data
end
function execute_from_socket, data, outputLUN
    data=strsplit(data,string(10b),/regex,/extract)
    ;remove the terminator line
    data=data[0:-2]
    ;remove the assignment part of the statement
    data[0]=strjoin((strsplit(data[0],'=',/regex,/extract))[1:*],'=')
    ;rejoin the strings
    data=strjoin(data,string(10b))

  err=execute(data)

  return, err
end

function define_global_from_socket, name, value
  (SCOPE_VARFETCH(name,LEVEL=-2,/ENTER))=value
  return, 1
end
function __post_plots__, data, outputLUN, FAST_SOCKET=fs
  for j=0,9 do begin
    catch, error_status
    if error_status ne 0 then begin & catch, /cancel & continue & endif
    
    wset, j
    imgcap=tvrd()
    s=size(imgcap)
    if ((s[1] eq 960) and (s[2] eq 540)) then if (total(imgcap) eq 0) then begin & wdelete, j & print, 'notta' & continue & endif
    write_jpeg, 'c:\wamp\vortex\IDL\imagestack\imgcap'+string(j,format='(I01)')+'.jpg', imgcap
  endfor
  return, 'yes it is here'
end
function __execute_from_socket__, data, outputLUN, FAST_SOCKET=fs
  response='<IDL<   '+(strsplit(data,string([10b,13b]),/regex,/extract))[1]+string([10b,13b])
  jfile='c:\wamp\www\IDL\acon.txt'
  if (not(lmgr(/demo))) then begin
    journal, jfile
    startflag='...begin journal output'+systime()
    journal, startflag
    ;openw, acon_unit, 'c:\wamp\www\IDL\acon.txt', /GET_LUN, /append
  endif
    err=0
    err=execute((strsplit(data,string([10b,13b]),/regex,/extract))[1])
  if (not(lmgr(/demo))) then begin
    journal
    readstring, jfile, log
  endif  
    if (not(err)) then response=response+ !error_state.msg+string([10b,13b])
    if (n_elements(log) gt 6) then response=response+'>IDL>   '+strjoin(strsplit(strjoin(log[6:*],string([10b,13b])),';',/EXTRACT,/REGEX),'>IDL>   ')+string([10b,13b])
    response=response+'--MainLevelVariables--'+strjoin(scope_varname(LEVEL=1),';')
  return, response
end

function __ping_idl_from_socket__, data, outputLUN, FAST_SOCKET=fs
  return, 'pong'
end


function __set_global_variable_from_socket__, data, outputLUN, FAST_SOCKET=fs
  variable_name=strmid(data,0,strpos(data,'='))
  variable_value=strmid(data,strpos(data,'='+string([10b,13b]))+3,strpos(data,'terminator',/REVERSE_SEARCH)-strpos(data,'='+string([10b,13b]))-6)
  
  (SCOPE_VARFETCH(variable_name,LEVEL=-2,/ENTER))=variable_value
  
  return, 1
end
function __get_global_variable_from_socket__, data, outputLUN, FAST_SOCKET=fs
  
  variable_name=(strsplit(strsplit(data,'variablename='+string([10b,13b]), /extract, /regex),string([10b,13b]), /extract, /regex))[0]
  ;nbytes=SOCK_SEND(outputLUN,SCOPE_VARFETCH(variable_name,LEVEL=-2,/ENTER))
  return, byte(SCOPE_VARFETCH(variable_name,LEVEL=-2,/ENTER))
end
function __compile_active_xtsm__, data, outputLUN, FAST_SOCKET=fs
  ; this parses the active_xtsm string at the main level
  xtsm_parse
  ;the following grabs all main-level variables that start with ACTIVE_TIMINGSTRING_, and concatenates them, prepending with the number of them as a single byte, and their lengths, in order, as 4-byte integers
  ;this should conform to the expectation of the get_control_arrays.vi on the PXI system
  mainlevelvars=scope_varname(level=1)
  timingstrings=strsplit(mainlevelvars[where(strpos(mainlevelvars,'ACTIVE_TIMINGSTRING_') ne -1)],'ACTIVE_TIMINGSTRING_',/regex,/extract)
  ;this adds number of strings
  response=byte(n_elements(timingstrings),0,1)
  ;this adds names, 8bytes a piece, and board initialization data, 16 bytes per board
  foreach timingstring, timingstrings do begin
    response=[response,byte(ulong64(n_elements(SCOPE_VARFETCH('ACTIVE_TIMINGSTRING_'+timingstring,LEVEL=1))),0,8),make_array(8-strlen(timingstring),value=32B,/byte),byte(timingstring)]
    response=[response,SCOPE_VARFETCH('ACTIVE_TIMINGDATA_'+timingstring,LEVEL=1)]
  endforeach
  ;this appends timingstrings
  foreach timingstring, timingstrings do begin
    response=[response,SCOPE_VARFETCH('ACTIVE_TIMINGSTRING_'+timingstring,LEVEL=1)]
  endforeach
  ;now append non-timingstring data
  return, response
end

function client_socket_read
  T0=systime(1)
  ; find/allocate some free file units
  get_lun, unit1
  ;connect these to a port (:8082), listening, and a file unit to extract and put data on
  socket, unit1, 'vortex.localhost/testclientsocket.html', '8081'
end

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;This procedure opens a TCP/IP port 8082 USING THE idl_tools API from Randall Frank (works only in 32-bit mode right now), and listens for a post.  The POST data is extracted, and a response is returned.
;POST form data should use the enctype='text/plain'.
;This shows transfer speed of 26MB/s without base64 en/decoding on Nate's laptop.  decoding can be done at 2MB/s  
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
function listen_and_respond_fast, response_function=rf, VERBOSE=vb, TIME=vbt, B64=b64
  T0=systime(1)
  ; connect these to a port (:8082), listening, and a file unit to extract and put data on
  socket = SOCK_CREATEPORT(8082) 
  socketacc= SOCK_ACCEPT(socket, BUFFER=10000000.,/nodelay)
  T1=systime(1)

  nqueries=0 & nreads=0
  ;wait, .001
; the following waits until there is something to read on the socket
  anbytes=0
  initqueries=0
  while (anbytes eq 0) do begin & wait, .001 & err=sock_query(socketacc,AVAILABLE_BYTES=anbytes)& initqueries++ & endwhile
  T1R=systime(1)
  allPOSTdata=bytarr(10.)
  nbytes=SOCK_RECV(socketacc,allPOSTdata,MAXIMUM_BYTES=10000.)
  T2=systime(1)
  
  ;  a blank line separates the header from data
  pos=strpos(allpostdata,string([10b,13b]))
  array=strmid(allpostdata,0,pos)
  data=strmid(allpostdata,pos+2)  

;look in header for any reference to stop_listening, and do so if found, sending an acknowledgement, closing the sockets, and return 0 from this routine 
  if (strpos(array,"stop_listening") ne -1) then begin 
      nbytes = SOCK_SEND(socketacc,byte('<b><span style="color:red;">IDLsocket terminated.</style></b>'))
      sc=SOCK_CLOSE(socketacc) & sc=SOCK_CLOSE(socket)
      return, 0
    endif
  
  
  ;extract the content-length line, extract the number of characters therein
  searchstring='Content-Length:'
  sl=strlen(searchstring)
  cls= strpos(array,searchstring) 
  cl=fix(strmid(array,cls+sl,strpos(array,string(10b),cls)-cls-sl),type=15)
    ;  extract the content-type line
  searchstring='Content-Type:'
  sl=strlen(searchstring)
  cts= strpos(array,searchstring) 
  ct=strupcase(strtrim(strmid(array,cts+sl,strpos(array,string(10b),cts)-cts-sl),2))
  
  ;retrieve remainder of data buffer if not already there
  anotherread=bytarr(10)
  while (strlen(data) lt cl) do begin 
    anbytes=0 & while (anbytes eq 0) do begin & wait,.001 & err=sock_query(socketacc,AVAILABLE_BYTES=anbytes) & nqueries+=1 & endwhile 
    nbytes=(SOCK_RECV(socketacc,anotherread))
    nreads+=1
    if (n_elements(anotherread) gt 0) then data=data+string(anotherread)
  endwhile
  T3=systime(1)
    
  ;if verbose, print out header data
  if keyword_set(vb) then print, 'header data:'
  if keyword_set(vb) then print, array


; if the encoding is form-data encoded with & field separators, split these into individual assignment statements
    if (ct eq 'APPLICATION/X-WWW-FORM-URLENCODED') then begin
      data=strsplit(data,'&',/regex,/extract)
        ;this next line converts values from base64 representation to decoded strings if we are using application/x-www-form-urlencoded
      for j=0,((size(data))[1]-1) do begin
        equalconvert=strjoin(strsplit(strmid(data[j],strpos(data[j],'=')+1,strlen(data[j])-strpos(data[j],'=')),'\%3D',/regex,/extract,/preserve_null  ),'=')
        plusconvert=strjoin(strsplit(strmid(equalconvert,strpos(equalconvert,'+')+1,strlen(equalconvert)-strpos(equalconvert,'+')),'\%2B',/regex,/extract,/preserve_null  ),'+')
        data[j]=strmid(data[j],0,strpos(data[j],'=')+1)+string(idl_base64(plusconvert))
      endfor
    endif
    
    ;this part requires 0.25s on a 500kB array if done with the commented-out strsplit.  it takes 15ms using strpos as done now
    if ((strsplit(ct,';',/extract))[0] eq 'MULTIPART/FORM-DATA') then begin
      tboundary=(strsplit(strmid(array,cts+sl,strpos(array,string(13b),cts)-cts-sl),'; BOUNDARY=',/extract,/regex,/fold_case))[1]
      
      T2=systime(1)
      ;find the positions of all the boundaries in the post data body
      if (fix((strsplit(!version.release,"\.",/regex,/extract))[0]) eq 8) then data1=!null else data1=''
      if (fix((strsplit(!version.release,"\.",/regex,/extract))[0]) eq 8) then poss=!null else poss=''
      pos0=0
      lastpos=-strlen('--'+tboundary+'--')
      while (pos0 ne -1) do begin 
        pos0=strpos(data,'--'+tboundary+'--',pos0+1) 
        if (pos0 ne -1) then poss=[poss,pos0] else break
        if (pos0 ne -1) then data1=[data1,strmid(data,lastpos+strlen('--'+tboundary+'--'),pos0-lastpos-strlen('--'+tboundary+'--'))]
        lastpos=pos0
      endwhile 
      
      if (fix((strsplit(!version.release,"\.",/regex,/extract))[0]) eq 8) then data=[data1,strmid(data,lastpos+strlen('--'+tboundary+'--'))] else data=[data1[1:*],strmid(data,lastpos+strlen('--'+tboundary+'--'))]
      
      ;data=strsplit(data,'--'+tboundary+'--',/regex,/extract)
      for j=0,(n_elements(data)-1) do begin
          temp=strmid(data[j],strpos(data[j],'name="')+strlen('name="'))
          data[j]=strmid(temp,0,strpos(temp,'"'))+'='+strmid(temp,3+strpos(temp,'"'))
      endfor
      
    endif
  
  ; if there is a response function defined on the first line, note it, and remove it from data
  pos=strpos(data[0],'IDLSocket_ResponseFunction=')
  if (pos ne -1) then begin    
    rf=IDL_VALIDNAME(strcompress(strmid(data[0],pos+strlen('IDLSocket_ResponseFunction=')),/Remove_all),/CONVERT_ALL)
    data=data[1:*]
  endif  
  
  if keyword_set(rf) then if (rf eq 'terminate_listen') then return, 0
  
  data=strjoin(data,string(10b))

  if keyword_set(vb) then print, 'POST data:'
  if keyword_set(vb) then print, data
  
  
  ; if there is a resonse function, call it and send its return value to the data stream, otherwise bounce the data back to sender as plain text 
  if keyword_set(rf) then begin 
    response=call_function(rf, data, socketacc, /FAST_SOCKET)
     T4=systime(1)
    if (strpos(strmid(data,0,4000),'IDLSPEEDTEST') ne -1) then begin 
      nbytes=SOCK_SEND(socketacc,data)
      T5=systime(1)
      response=strjoin(string([fix(1000.*(T3-T1R)),fix(1000.*(T5-T4)),fix(1000.*(T1R-T1)),nqueries,nreads,initqueries]),',')
    endif
    if ((size(response))[-2] eq 7) then nbytes = SOCK_SEND(socketacc,string(strlen(response),format='(I016)')) else nbytes = SOCK_SEND(socketacc,string(n_elements(response),format='(I016)'))
    
    nbytes = SOCK_SEND(socketacc,byte(response)) 
    endif else begin nbytes = SOCK_SEND(socketacc,string(strlen(data),format='(I016)')) & nbytes = SOCK_SEND(socketacc,data) &  T4=systime(1) & endelse
 


  ; free the sockets
;  nbytes=SOCK_SEND(socketacc, string(T4-T1))
  sc=SOCK_CLOSE(socketacc) 
;  if (sc eq -1) then stop
  sc=SOCK_CLOSE(socket)
;  if (sc eq -1) then stop

  T5=systime(1)
  if keyword_set(vbt) then begin
    TT=[T0,[T2,T3,T4,T5]-T1]
    TTlabel=["time request received","data load","header searches and base64 conversion","responsefunction execution","freeing socket"]
    for j=0,4 do print, TTlabel[j], TT[j]
  endif
  return, 1
end
PRO READSTRING,Filename,Array,MAXLINE=maxline
;+
; NAME:                 readstring
;       
; PURPOSE:  Read text file into a string array.
;
; CATEGORY: Text processing
;
; CALLING SEQUENCE: readstring,filename,array
;
; INPUT ARGUMENTS:  
;       filename - input file name
;
; OUTPUT ARGUMENTS:
;       array - string array with contents of file
;
; INPUT KEYWORD PARAMETER:
;       maxline - maximum number of lines allowed; default=1000
;
; MODIFICATION HISTORY:
;   30 Jun. 1997 - Written.  RSH/HSTX
;   28 Jun. 2000 - Square bracket subscripts.  RSH
;-
IF n_elements(maxline) LT 1 THEN maxline=1000
array = strarr(maxline)
openr,lun,filename,/get_lun
line = ''
i=0
WHILE NOT eof(lun) DO BEGIN
    readf,lun,line
    array[i] = line
    i = i + 1
ENDWHILE
i = i - 1
array = array[0:i]
free_lun,lun
RETURN
END
