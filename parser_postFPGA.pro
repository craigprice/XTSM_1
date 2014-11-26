FUNCTION valid_num, string, value, INTEGER=integer
 On_error,2
 compile_opt idl2 
 
; A derivation of the regular expressions below can be found on 
; http://wiki.tcl.tk/989

   if keyword_set(INTEGER) then $ 
    st = '^[-+]?[0-9][0-9]*$'  else $                    ;Integer
     st = '^[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)([eEdD][-+]?[0-9]+)?$' ;F.P.
   
;Simple return if we just need a boolean test.
    if N_params() EQ 1 then return, stregex(strtrim(string,2),st,/boolean)

   
      vv = stregex(strtrim(string,2),st,/boolean)      
      if size(string,/N_dimen) EQ 0 then begin     ;Scalar
         if vv then $
            value= keyword_set(integer) ? long(string) : double(string) 
      endif else begin                             ;Array 
         
      g = where(vv,Ng)
      if Ng GT 0 then begin      ;Need to create output vector
        if keyword_set(integer) then begin 
              value = vv*0L 
              value[g] = long(string[g])
        endif else begin 
                value = replicate(!VALUES.D_NAN,N_elements(vv))
                value[g] = double(string[g])
        endelse 
        endif   
        endelse 
     
       return,vv
      end

function open_xml, file

  oDocument = OBJ_NEW('IDLffXMLDOMDocument')  
  oDocument->Load, FILENAME=file , /EXCLUDE_IGNORABLE_WHITESPACE
  return, oDocument

end

function open_xml_from_string, stringin

  oDocument = OBJ_NEW('IDLffXMLDOMDocument')  
  oDocument->Load, STRING=stringin , /EXCLUDE_IGNORABLE_WHITESPACE
  return, oDocument

end

function find_children, object,tagname 
;returns direct descendents of specific tagname as a list of children's indices
children=object->GetChildNodes()
indices=!NULL
for k=0, (children->GetLength()-1) do if ((children->item(k))->GetNodeName() eq tagname) then indices=[k,[indices]]
return, indices
end

function find_named_node, parent, name, TYPE=type
;returns the first descendent node with the specified name
  if (KEYWORD_SET(type)) then candidates=parent->getElementsByTagName(type) else candidates=parent->getChildNodes()
  for j=0, (candidates->GetLength()-1) do if ((candidates->item(j))->GetAttribute('Name') eq name) then break
  if (j ne (candidates->GetLength()-1)) then return, candidates->item(j) else return, !Null
end


function parseSequence, theObject, channelMapObject, edgearray, intervalarray, intervaldefns, uidlist, HARVEST_INTERVAL_TIMING_GROUP=hitg, HARVEST_TIMES=ht
;this function recursively dives into the subsequence trees and translates variable-containing expressions to numeric values
;the HARVEST keywords allow a 'second-pass' through the parser to convert each interval belonging to a channel in the the given timing group into edges, which are heaped (time-sorted) into the edgearray
if (keyword_set(ht)) then htind=indgen(n_elements(ht),/ULONG)

shotnumber=SCOPE_VARFETCH('next_shotnumber', LEVEL=1)   

children=theObject->GetChildNodes()

;get parameters defined at this level and above, execute their definitions
; to avoid trying to access out-of-scope variables, this should search "up the parentNode chain" for other parameters (defining them downward, so local defns shadow global)
err=1
; find the number of parents above this node up to sequence container
p=theObject & numparents=0
while (p->GetNodeName() ne 'body') do begin p=p->GetParentNode() & numparents+=1 & endwhile

; go through all parents, finding parameters
for parentwalk=0, numparents do begin
; first find the parent of interest, starting from sequence, going downward
  p=theObject
  for m=0, numparents-parentwalk-1 do p=p->GetParentNode()
; scan its children for parameters
  thesechildren=p->GetChildNodes()
  param_list=find_children(p,'Parameter')
  for k=0, (n_elements(param_list)-1) do begin
      paramname=((((thesechildren->item(param_list[k]))->GetElementsByTagName('Name'))->item(0))->GetFirstChild())->GetNodeValue()
      err=execute(paramname+'='+((((thesechildren->item(param_list[k]))->GetElementsByTagName('Value'))->item(0))->GetFirstChild())->GetNodeValue())
      if (not(err)) then begin (((thesechildren->item(param_list[k]))->GetElementsByTagName('Value'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 

      err=execute('temp='+((((thesechildren->item(param_list[k]))->GetElementsByTagName('Value'))->item(0))->GetFirstChild())->GetNodeValue())
      err=1
      (((thesechildren->item(param_list[k]))->GetElementsByTagName('Value'))->item(0))->SetAttribute,"currentvalue",STRCOMPRESS(temp,/REMOVE_ALL)
  endfor
endfor

;get the subsequence start time, add to parent's starttime T00 (if exists), define as T0, append as 'currentvalue' attribute in DOM tree

parentsstart_list=find_children(theObject->GetParentNode(),'StartTime')
if (parentsstart_list ne !NULL) then T00=((((theObject->GetParentNode())->GetChildNodes())->item(parentsstart_list[0]))->GetAttributes())->GetNamedItem('currentvalue') else T00=0

starttime_list=find_children(theObject,'StartTime')
if (starttime_list ne !NULL) then begin 
  err=execute('T0=T00 +'+(((children)->item(starttime_list[0]))->GetFirstChild())->GetNodeValue() ) 
  if (not(err)) then begin (children->item(starttime_list[0]))->SetAttribute,"parseerror",!error_state.msg  & endif else (children->item(starttime_list[0]))->SetAttribute,"currentvalue",STRCOMPRESS(String(T0),/REMOVE_ALL)
  endif else err=execute('T0=T00') 
;now get edges at current level, parse them into numerical values, assemble an edgearray

;find all SerialTransfer objects at this level; parse into clock channel interval, data channel interval and update channel edge
if (not(KEYWORD_SET(hitg))) then begin
  ;first get all serialTransfer nodes
  SerialTransfer_list=find_children(theObject,'SerialTransfer')
  ;loop through each found
  for k=0, (n_elements(SerialTransfer_list)-1) do begin
    print, 'processing serial transfer node:'+string(k)
    ;locate the corresponding SerialGroup node in the ChannelMap
    serialGroupObject=getSerialGroup(channelMapObject,((((children->item(SerialTransfer_list[k]))->GetElementsByTagName('OnSerialGroup'))->item(0))->GetFirstChild())->GetNodeValue())
    if ( ((children->item(SerialTransfer_list[k]))->GetElementsByTagName('Name'))->GetLength() gt 0 ) then serialname=((((children->item(SerialTransfer_list[k]))->GetElementsByTagName('Name'))->item(0))->GetFirstChild())->GetNodeValue() else serialname=''    
    ;identify the clock period
    period=(((serialGroupObject->GetElementsByTagName('TimeBase'))->item(0))->GetFirstChild())->GetNodeValue()

    ;get the update time and parse it
    updatetimestring=((((children->item(SerialTransfer_list[k]))->GetElementsByTagName('UpdateTime'))->item(0))->GetFirstChild())->GetNodeValue()
    err=1
    err=execute('updatetime='+updatetimestring)
    if (not(err)) then begin (((children->item(SerialTransfer_list[k]))->GetElementsByTagName('UpdateTime'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 

        ; get the unique id for this serialTransfer if it exists - if it does not assign one.
        thisuid=(children->item(SerialTransfer_list[k]))->GetAttribute('uid')
        if (thisuid eq '') then begin thisuid=string(fix(1000000*systime(1)+k,type=15)) & (children->item(SerialTransfer_list[k]))->SetAttribute, 'uid', thisuid & endif 
        uidindex=where(uidlist eq thisuid)
        if (uidindex eq -1) then begin uidlist=[uidlist,thisuid] & uidindex=n_elements(uidlist)-1 & endif 


    ;identify the data channel, create an interval to output that data
    datachannelName=(((serialGroupObject->GetElementsByTagName('DataChannel'))->item(0))->GetFirstChild())->GetNodeValue()
    datastring=((((children->item(SerialTransfer_list[k]))->GetElementsByTagName('DataString'))->item(0))->GetFirstChild())->GetNodeValue()
    err=1
    err=execute('serialdataarray='+datastring)
    if (not(err)) then begin (((children->item(SerialTransfer_list[k]))->GetElementsByTagName('DataString'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 

    serialtimes=findgen(n_elements(serialdataarray))*FLOAT(period)
    serialtimesstring=STRING(serialtimes, FORMAT='("[",'+STRING(N_ELEMENTS(serialtimes)-1)+'(F0,","),F0,"]")')
  ;create a data-channel interval containing an explicit times/values list
    datainterval=theObject->insertBefore((theObject->GetOwnerDocument())->CreateElement('Interval'),children->item(SerialTransfer_list[k]))
    datainterval->SetAttribute,"parser_temp","Serial Update"
    datainterval->SetAttribute,"uid", thisuid
    subnodes=[['OnChannel',datachannelName],['Values',datastring],['Times',serialtimesstring],['EndTime',STRING(FLOAT(updatetime)-FLOAT(period))],['StartTime',STRING(FLOAT(updatetime)-(n_elements(serialdataarray)+1)*FLOAT(period))],['TResolution',period],['Name','_datastring_:'+serialname]]
    for s=0,((size(subnodes))[2]-1) do begin
      nextnode=datainterval->AppendChild((theObject->GetOwnerDocument())->CreateElement(subnodes[0,s]))
      nextnodetext=nextnode->AppendChild((theObject->GetOwnerDocument())->CreateTextNode(subnodes[1,s]))
    endfor

    ;identify clock channel, create an interval with appropriate output times and alternating values
    clockchannelName=(((serialGroupObject->GetElementsByTagName('ClockChannel'))->item(0))->GetFirstChild())->GetNodeValue()
    clockvalues=INDGEN(n_elements(serialdataarray)) mod 2
    clockstring=STRING(clockvalues, FORMAT='("[",'+STRING(N_ELEMENTS(serialtimes)-1)+'(F0,","),F0,"]")')
    serialclocktimes=serialtimes+FLOAT(period)/2.
    serialclocktimesstring=STRING(serialclocktimes, FORMAT='("[",'+STRING(N_ELEMENTS(serialtimes)-1)+'(F0,","),F0,"]")')
    clockinterval=theObject->insertBefore((theObject->GetOwnerDocument())->CreateElement('Interval'),children->item(SerialTransfer_list[k]))
    clockinterval->SetAttribute,"parser_temp","Serial Update"
    clockinterval->SetAttribute,"uid", thisuid
    subnodes=[['OnChannel',clockchannelName],['Values',clockstring],['Times',serialclocktimesstring],['EndTime',STRING(FLOAT(updatetime)-FLOAT(period))],['StartTime',STRING(FLOAT(updatetime)-(n_elements(serialdataarray)+1)*FLOAT(period))],['TResolution',period],['Name','_clockstring_:'+serialname]]
    for s=0,((size(subnodes))[2]-1) do begin
      nextnode=clockinterval->AppendChild((theObject->GetOwnerDocument())->CreateElement(subnodes[0,s]))
      nextnodetext=nextnode->AppendChild((theObject->GetOwnerDocument())->CreateTextNode(subnodes[1,s]))
    endfor
    
    ;identify update strobe channel; add appropriate edge
    updatechannelName=(((serialGroupObject->GetElementsByTagName('UpdateChannel'))->item(0))->GetFirstChild())->GetNodeValue()
    updateedge=theObject->insertBefore((theObject->GetOwnerDocument())->CreateElement('Edge'),children->item(SerialTransfer_list[k]))
    subnodes=[['OnChannel',updatechannelName],['Value','1'],['Time',updatetimestring]]
    for s=0,((size(subnodes))[2]-1) do begin
      nextnode=updateedge->AppendChild((theObject->GetOwnerDocument())->CreateElement(subnodes[0,s]))
      nextnodetext=nextnode->AppendChild((theObject->GetOwnerDocument())->CreateTextNode(subnodes[1,s]))
    endfor
    updateedge->SetAttribute,"parser_temp","Serial Update"
    updateedge->SetAttribute,"uid", thisuid

  endfor

endif

;find edges at this level, begin looping through them
if (not(KEYWORD_SET(hitg))) then begin
  edge_list=find_children(theObject,'Edge')
  for k=0, (n_elements(edge_list)-1) do begin  ;k indexes the children of theObject which are edges using the lookup edge_list
      ;first retrieve channel parameters for this edge, if the channel exists in header's channelMapObject
      channelObject=getChannel(channelMapObject,((((children->item(edge_list[k]))->GetElementsByTagName('OnChannel'))->item(0))->GetFirstChild())->GetNodeValue())    
      if (channelObject ne !Null) then begin 
          param_list=channelObject->GetElementsByTagName('Parameter') ; we will collect _all_ descendent parameters inside the corresponding channel element 
          for m=0, (param_list->GetLength()-1) do begin
            err=execute(((((param_list->item(m))->GetElementsByTagName('Name'))->item(0))->GetFirstChild())->GetNodeValue()+'='+((((param_list->item(m))->GetElementsByTagName('Value'))->item(0))->GetFirstChild())->GetNodeValue())
          endfor
      endif else begin
      ;if the channel is undefined, note it and skip
      (((children->item(edge_list[k]))->GetElementsByTagName('Value'))->item(0))->SetAttribute,"parseerror","Channel does not exist"
      continue
      endelse
      ;the following is the fundamental timestep for this channel - ideally it would be pulled out of the head data, but for now i am just setting it to 25ns.
      basetime=double(0.000025)
      ; now need to parse edge fields into numeric values
      ;execute the time and voltage definitions, allowing one to depend on the other - do not yet have an error flag for circular definitions
      err=1   ;this is an error-catching flag
        if (STRPOS(((((children->item(edge_list[k]))->GetElementsByTagName('Value'))->item(0))->GetFirstChild())->GetNodeValue(),'T') NE -1) then begin 
        err=execute('T=double(round((T0+'+((((children->item(edge_list[k]))->GetElementsByTagName('Time'))->item(0))->GetFirstChild())->GetNodeValue()+')/basetime))*basetime')
        if (not(err)) then begin (((children->item(edge_list[k]))->GetElementsByTagName('Time'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
        err=1
        err=execute('V='+((((children->item(edge_list[k]))->GetElementsByTagName('Value'))->item(0))->GetFirstChild())->GetNodeValue())
        if (not(err)) then begin (((children->item(edge_list[k]))->GetElementsByTagName('Value'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
        err=1
        (((children->item(edge_list[k]))->GetElementsByTagName('Value'))->item(0))->SetAttribute,"currentvalue",STRCOMPRESS(String(V),/REMOVE_ALL)
        (((children->item(edge_list[k]))->GetElementsByTagName('Time'))->item(0))->SetAttribute,"currentvalue",STRCOMPRESS(String(T),/REMOVE_ALL)
        endif else begin
        err=execute('V='+((((children->item(edge_list[k]))->GetElementsByTagName('Value'))->item(0))->GetFirstChild())->GetNodeValue())
        if (not(err)) then begin (((children->item(edge_list[k]))->GetElementsByTagName('Value'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
        err=1
        err=execute('T=double(round((T0+'+((((children->item(edge_list[k]))->GetElementsByTagName('Time'))->item(0))->GetFirstChild())->GetNodeValue()+')/basetime))*basetime')
        if (not(err)) then begin (((children->item(edge_list[k]))->GetElementsByTagName('Time'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
        err=1
        (((children->item(edge_list[k]))->GetElementsByTagName('Value'))->item(0))->SetAttribute,"currentvalue",STRCOMPRESS(String(V),/REMOVE_ALL)
        (((children->item(edge_list[k]))->GetElementsByTagName('Time'))->item(0))->SetAttribute,"currentvalue",STRCOMPRESS(String(T),/REMOVE_ALL)
        endelse
        
        ;rewrite the voltage and time values for this edge -heap the edges and intervals into time-ordered 2D arrays [[T,C,V],[T,C,V],...], one for each timing group
        ;where T is the universal sequence time, C is the channel group index, V is the output voltage
        TimingGroup=((((channelObject->GetElementsByTagName('TimingGroup'))->item(0))->GetFirstChild())->GetNodeValue())
        TimingGroupIndex=((((channelObject->GetElementsByTagName('TimingGroupIndex'))->item(0))->GetFirstChild())->GetNodeValue())
        
        ; get the unique id for this edge if it exists - if it does not assign one.
        thisuid=(children->item(edge_list[k]))->GetAttribute('uid')
        if (thisuid eq '') then begin thisuid=string(fix(1000000*systime(1)+k,type=15)) & (children->item(edge_list[k]))->SetAttribute, 'uid', thisuid & endif 
        uidindex=where(uidlist eq thisuid)
        if (uidindex eq -1) then begin uidlist=[uidlist,thisuid] & uidindex=n_elements(uidlist)-1 & endif 
        ;if ((n_elements(edgearray[2,*])-2) ne 0) then edgearray=[[edgearray[*,0:(m-1)]],[TimingGroup,TimingGroupIndex,T,V],[edgearray[*,m:*]]] else  edgearray=[[edgearray[*,0]],[TimingGroup,TimingGroupIndex,T,V],[edgearray[*,1]]]    ;address times as edgearray[2,*] 
        edgearray=[[edgearray],[TimingGroup,TimingGroupIndex,T,V,uidindex]]
        

  endfor
if (edgearray ne !NULL) then edgearray=edgearray[*,sort(edgearray[2,*])]
endif else begin

  ; below is an algorithm to replace the 0th element of edgearray with the corresponding time index.  efficient by using the time-sorting already there 
  ; while edge index < length
  ; advance time series index until match
  edgearray=edgearray[*,sort(edgearray[2,*])]  ;this sorting command was inserted after adding the times/values interval functionality - its edge insertion doesn't preserve time-ordering
  ii=0
  jj=0
  if ((size(edgearray))[0] eq 1) then edgearray[0]=0 else $ ; the following search sometimes does not execute properly because the times are represented to too high precision (caution: print statements don't show all digits)
    while (ii le ((size(edgearray))[2]-1)) do begin while (( edgearray[2,ii]- ht[jj] ) gt 0.0001) do jj++ & edgearray[0,ii]=htind[jj] & ii++ & endwhile
endelse  ;this else results if we are in harvest pass

;INPUT THE INTERVALS in theObject, PARSE VARIABLES AND EVALUATE ALL TIMES TO NUMERIC VALUES
interval_list=find_children(theObject,'Interval')


for k=0, (n_elements(interval_list)-1) do begin
     ;first retrieve channel parameters for this interval, if the channel exists in header's channelMapObject
    channelObject=getChannel(channelMapObject,((((children->item(interval_list[k]))->GetElementsByTagName('OnChannel'))->item(0))->GetFirstChild())->GetNodeValue())    
    if (channelObject ne !Null) then begin 
        param_list=channelObject->GetElementsByTagName('Parameter') ; we will collect _all_ descendent parameters inside the corresponding channel element 
        for m=0, (param_list->GetLength()-1) do begin
          err=execute(((((param_list->item(m))->GetElementsByTagName('Name'))->item(0))->GetFirstChild())->GetNodeValue()+'='+((((param_list->item(m))->GetElementsByTagName('Value'))->item(0))->GetFirstChild())->GetNodeValue())
        endfor
    endif

    ;get the timing group and the group index for this interval
    TimingGroup=((((channelObject->GetElementsByTagName('TimingGroup'))->item(0))->GetFirstChild())->GetNodeValue())
    TimingGroupIndex=((((channelObject->GetElementsByTagName('TimingGroupIndex'))->item(0))->GetFirstChild())->GetNodeValue())
    
    if (KEYWORD_SET(hitg)) then if (FIX(TimingGroup) ne hitg) then continue   ;if harvesting, and this is not in the harvest timing group, skip this interval
    
    ; parse the start and end times of this interval
    err=execute('T1=T0+'+((((children->item(interval_list[k]))->GetElementsByTagName('StartTime'))->item(0))->GetFirstChild())->GetNodeValue())
    if (not(err)) then begin (((children->item(interval_list[k]))->GetElementsByTagName('StartTime'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
    err=1
    err=execute('T2=T0+'+((((children->item(interval_list[k]))->GetElementsByTagName('EndTime'))->item(0))->GetFirstChild())->GetNodeValue())
    if (not(err)) then begin (((children->item(interval_list[k]))->GetElementsByTagName('EndTime'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
    err=1
    ; update their numerical values in the currentvalue property of the DOM node
    (((children->item(interval_list[k]))->GetElementsByTagName('StartTime'))->item(0))->SetAttribute,"currentvalue",STRCOMPRESS(String(T1),/REMOVE_ALL)
    (((children->item(interval_list[k]))->GetElementsByTagName('EndTime'))->item(0))->SetAttribute,"currentvalue",STRCOMPRESS(String(T2),/REMOVE_ALL)

    ; get the unique id for this interval if it exists - if it does not assign one.
    thisuid=(children->item(interval_list[k]))->GetAttribute('uid')
    if (thisuid eq '') then begin thisuid=string(fix(1000000*systime(1)+k,type=15)) & (children->item(interval_list[k]))->SetAttribute, 'uid', thisuid & endif 
    uidindex=where(uidlist eq thisuid)
    if (uidindex eq -1) then begin uidlist=[uidlist,thisuid] & uidindex=n_elements(uidlist)-1 & endif 


  ;if this is a times/values explicitly defined interval and we are not harvesting, tabulate the time/value pairs as edges, if we are harvesting, skip this interval
    IF (((children->item(interval_list[k]))->GetElementsByTagName('Times'))->GetLength() gt 0) THEN BEGIN
          if (KEYWORD_SET(hitg)) then continue
          err=execute('TI='+((((children->item(interval_list[k]))->GetElementsByTagName('Times'))->item(0))->GetFirstChild())->GetNodeValue())
          if (not(err)) then begin (((children->item(interval_list[k]))->GetElementsByTagName('Times'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
          err=1
          ; gaurantee that no edges lie outside interval window
          TI=TI[where((TI gt 0) and (TI lt (T2-T1)))]
          T=TI+T1
          if (((children->item(interval_list[k]))->GetElementsByTagName('Values'))->GetLength() gt 0) then intervaldef=((((children->item(interval_list[k]))->GetElementsByTagName('Values'))->item(0))->GetFirstChild())->GetNodeValue()
          err=execute('V='+intervaldef)
          if (not(err)) then begin (((children->item(interval_list[k]))->GetElementsByTagName('Values'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
          err=1
          for m=0,(n_elements(T)-1) do edgearray=[[edgearray],[TimingGroup,TimingGroupIndex,T[m],V[m],uidindex]]
          ;stop
          continue
    ENDIF
  

    ; get time resolution (unnecessary during harvest) - if not there, set to default value, unless this interval is a times/values list
    if (not(KEYWORD_SET(hitg))) then begin
      IF (((children->item(interval_list[k]))->GetElementsByTagName('TResolution'))->GetLength() gt 0) THEN BEGIN
          thisnode=((children->item(interval_list[k]))->GetElementsByTagName('TResolution'))->item(0)
          IF (thisnode->hasChildNodes()) THEN TRESFIELD=DOUBLE((thisnode->GetFirstChild())->getNodeValue()) ELSE TRESFIELD='0.02D'
          IF  ( valid_num (TRESFIELD)  ) THEN TIMERESOLUTION=DOUBLE(TRESFIELD) ELSE TIMERESOLUTION=0.02D
          ENDIF ELSE TIMERESOLUTION=0.02D
      ; create two time arrays - universal time and ramp time, and corresponding value array (also unnecessary during harvest)
      T=FINDGEN((T2-T1)/TIMERESOLUTION)*TIMERESOLUTION+T1
      TI=FINDGEN((T2-T1)/TIMERESOLUTION)*TIMERESOLUTION
;      ; if an explicit set of times is given, override the above declarations
;      IF (((children->item(interval_list[k]))->GetElementsByTagName('Times'))->GetLength() gt 0) THEN BEGIN
;          err=execute('TI='+((((children->item(interval_list[k]))->GetElementsByTagName('Times'))->item(0))->GetFirstChild())->GetNodeValue())
;          if (not(err)) then begin (((children->item(interval_list[k]))->GetElementsByTagName('Times'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
;          T=TI+T1
;          TIMERESOLUTION=min((T-SHIFT(T,1))[1:*])
;      ENDIF
    endif else begin 
      T=ht[where((ht GE T1) and (ht LT T2))]   ;during harvest we take our time values from the 'best compromise' time edges determined after first parse
      TI=ht[where((ht GE T1) and (ht LT T2))]-T1
      htindT=htind[where((ht GE T1) and (ht LT T2))]  ;this index is carried to denote the rank of a given time edge
;      ;if this is a times/values list-defined interval, select the best compromise times closest to the times list
;      IF (((children->item(interval_list[k]))->GetElementsByTagName('Times'))->GetLength() gt 0) THEN BEGIN
;          TBC=T & TIBC=TI   ; stash the best compromise times, reread the list
;          err=execute('TI='+((((children->item(interval_list[k]))->GetElementsByTagName('Times'))->item(0))->GetFirstChild())->GetNodeValue())
;          if (not(err)) then begin (((children->item(interval_list[k]))->GetElementsByTagName('Times'))->item(0))->SetAttribute,"parseerror",!error_state.msg & continue & endif 
;          T=TI+T1
;          T=TBC[(value_locate(TBC,T)+1.*FLOAT((ABS(TBC[value_locate(TBC,T)]-T)) GT (ABS(TBC[(value_locate(TBC,T)+1) < (N_ELEMENTS(TBC)-1) ]-T))))]
;          TI=T-T1
;          htindT=htind[(value_locate(TBC,T)+1.*FLOAT((ABS(TBC[value_locate(TBC,T)]-T)) GT (ABS(TBC[(value_locate(TBC,T)+1) < (N_ELEMENTS(TBC)-1) ]-T))))]
;         ENDIF       
    endelse
    ;get this interval's value(s) formula, and execute it - if it does not yield an array of same size of times, makeup by padding end value
    if (((children->item(interval_list[k]))->GetElementsByTagName('Value'))->GetLength() gt 0) then intervaldef=((((children->item(interval_list[k]))->GetElementsByTagName('Value'))->item(0))->GetFirstChild())->GetNodeValue()
;    if (((children->item(interval_list[k]))->GetElementsByTagName('Values'))->GetLength() gt 0) then intervaldef=((((children->item(interval_list[k]))->GetElementsByTagName('Values'))->item(0))->GetFirstChild())->GetNodeValue()
    err=execute('V='+intervaldef)
    if (not(err)) then begin (((children->item(interval_list[k]))->GetElementsByTagName('Value'))->item(0))->SetAttribute,"parseerror",!error_state.msg  & continue & endif 
    err=1

   ; get voltage resolution - if not there, set to default value
    IF (((children->item(interval_list[k]))->GetElementsByTagName('VResolution'))->GetLength() gt 0) THEN BEGIN
          thisnode=((children->item(interval_list[k]))->GetElementsByTagName('VResolution'))->item(0)
          IF (thisnode->hasChildNodes()) THEN VRESFIELD=(thisnode->GetFirstChild())->getNodeValue() ELSE VRESFIELD='0.005D'
          IF  ( valid_num (VRESFIELD)  ) THEN VRESOLUTION=FLOAT(VRESFIELD) ELSE VRESOLUTION=0.005D
    ENDIF ELSE VRESOLUTION=0.005D

   ; coerce output values to voltage resolution
   V=ROUND(V/VRESOLUTION,/L64)*VRESOLUTION
   ;drop subsequent repeated elements to conserve memory and update strobes (this only removes the edges in the sparse representation - they will be replaced by the formation of a dense control array)
   T=T[[0,uniq(V)+1]]
   if ((KEYWORD_SET(hitg))) then htindT=htindT[[0,uniq(V)+1]]
   V=V[[0,uniq(V)+1]]
    
   ;reset or create timingdata node for this interval to hold a 2D array of time_value pairs separated by __'s
   ;need to adjust this so during harvest we create a datanode of name 'actual', and during first-pass parse create datanode named 'ideal' 
   timingdata=STRJOIN(STRCOMPRESS(STRJOIN(TRANSPOSE(STRING([[T],[V]])),'_'),/REMOVE_ALL),'__')
   ;if no timingdata node, append one
   if (((children->item(interval_list[k]))->GetElementsByTagName('TimingData'))->GetLength() eq 0) then $  
        timingdatanode=(children->item(interval_list[k]))->AppendChild((theObject->getOwnerDocument())->createElement("TimingData")) $
      else timingdatanode=((children->item(interval_list[k]))->GetElementsByTagName('TimingData'))->item(0)
   ; if no data node on timingdata, append one
   if ((timingdatanode->GetElementsByTagName('Data'))->GetLength() eq 0) then $ 
      timingdatanodedatanode=(((((children->item(interval_list[k]))->GetElementsByTagName('TimingData'))->item(0))))->AppendChild((theObject->getOwnerDocument())->createElement("Data")) $
      else timingdatanodedatanode=(timingdatanode->GetElementsByTagName('Data'))->item(0)         
   
   if (KEYWORD_SET(hitg)) then thisname='actual' else thisname='ideal'
   ;if there are ARRAY2D on this data node named thisname, destroy them 
   while (find_named_node(timingdatanodedatanode,thisname,TYPE='ARRAY2D') ne !NULL) do err=timingdatanodedatanode->RemoveChild(find_named_node(timingdatanodedatanode,thisname,TYPE='ARRAY2D'))
   ;create an ARRAY2D node, set name attribute to thisname
   arraynode=timingdatanodedatanode->AppendChild((theObject->getOwnerDocument())->CreateElement("ARRAY2D"))
   arraynode->SetAttribute, 'Name', thisname
   ;populate the text field with the array data
   tnodetext=arraynode->AppendChild((theObject->getOwnerDocument())->CreateTextNode(timingdata))
   


    ;find the appropriate time-ordered place to insert this interval into the intervalarray of all intervals under sequence   
   if (not(KEYWORD_SET(hitg))) then begin
    for m=(size(intervalarray))[2]-1,0,-1 do if (intervalarray[2,m] GE T1) then break
    ;insert it
    intervalarray=[[intervalarray[*,0:(m-1)]],[TimingGroup,TimingGroupIndex,T1,T2,VResolution,TIMERESOLUTION,k,uidindex],[intervalarray[*,m:*]]]      ;address times as edgearray[2,*]
    ;keep track of all interval value formulas in intervaldefns
    intervaldefns=[[intervaldefns],intervaldef]
   endif
   ;on harvesting call, insert edges into edgearray
   if (KEYWORD_SET(hitg)) then begin
    ;merge the sorted lists in edgearray and interval time T,V.
    ;advance an index through edgearray (already selected out by timing group in main call) and time value ,taking smaller value out of indices for one or the other
    newedgearray=!null
    ei=0 & ii=0
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;issue here;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
    ;if (n_elements(edgearray) le 10) then newedgearray=[[htindT],make_array(n_elements(T),value=TimingGroupIndex),[T],[V]] else begin
    if (0) then newedgearray=transpose([[[htindT]],[make_array(n_elements(T),value=TimingGroupIndex)],[[T]],[[V]],[make_array(n_elements(T),value=uidindex)]]) else begin
      while((ei le ((size(edgearray))[2]-1)) and (ii le (n_elements(T)-1) ) ) do begin
        if (edgearray[2,ei] le T[ii]) then begin newedgearray=[[newedgearray],[edgearray[*,ei]]] & ei+=1 & continue & endif
        if (edgearray[2,ei] gt T[ii]) then begin newedgearray=[[newedgearray],[htindT[ii],TimingGroupIndex,T[ii],V[ii],uidindex]] & ii+=1 & continue & endif
        ;if (edgearray[2,ei] eq T[ii]) then begin 
      endwhile
      ; once this is done, append all remaining edges on the array not yet looped entirely through
      if (ei eq (size(edgearray))[2]) then newedgearray=[[newedgearray],[htindT[ii:*],TimingGroupIndex,T[ii:*],V[ii:*],uidindex]] else newedgearray=[[newedgearray],[edgearray[*,ei:*]]]
    endelse  
    
    edgearray=newedgearray
   endif
    
endfor  ; ends the k-loop over intervals

; now dive by calling this function on all subsequences in theObject
; pass edgearray, intervalarray, intervaldefns to be added to and returned
SubSequence_List=find_children(theObject,'SubSequence')
for j=0, (n_elements(SubSequence_List)-1) do begin
    if (not(KEYWORD_SET(hitg))) then err=ParseSequence(children->item(SubSequence_List[j]), channelMapObject, edgearray, intervalarray, intervaldefns, uidlist ) $
      else err=ParseSequence(children->item(SubSequence_List[j]), channelMapObject, edgearray, intervalarray, intervaldefns, uidlist, HARVEST_INTERVAL_TIMING_GROUP=hitg, HARVEST_TIMES=ht ) ;finish
endfor
  
  return, 1
end

function getChannel, theChannelMapObject, ChannelName
;returns a channel by name
  channelList=(theChannelMapObject->GetElementsByTagName('Channel'))
  for j=0, (channelList->GetLength())-1 do if (((((ChannelList->item(j))->GetElementsByTagName('ChannelName'))->item(0))->GetFirstChild())->GetNodeValue() EQ ChannelName) then break
  return, channelList->item(j) 
end
function getSerialGroup, theChannelMapObject, ChannelName
;returns a channel by name
  SerialGroupList=(theChannelMapObject->GetElementsByTagName('SerialGroup'))
  for j=0, (SerialGroupList->GetLength())-1 do if (((((SerialGroupList->item(j))->GetElementsByTagName('Name'))->item(0))->GetFirstChild())->GetNodeValue() EQ ChannelName) then break
  return, SerialGroupList->item(j) 
end


function DOM_to_treestring, theObject, level
;This function prints a tree diagram of an xml object, level should be supplied with 0; function is recursive
theChildrenList=theObject->GetChildNodes()
for j=0, (theChildrenList->GetLength()-1) do begin
  tabs=''
  for k=0, level do tabs=tabs+'-'
  print, tabs+(theChildrenList->Item(j))->GetNodeName() 
  nullvoid=DOM_to_treestring(theChildrenList->Item(j), level+1)
  endfor

treestring=''
return, treestring

end

function DOM_trimwhitespaces, theObject, level
;This function is meant to remove nodes generated by tabs and newlines in XML data, but it does not find the newlines due to the lack of good string processing functions in IDL
theChildrenList=theObject->GetChildNodes()
for j=0, (theChildrenList->GetLength()-1) do begin
  if (((theChildrenList->Item(j))->GetNodeName()) EQ "#text") then begin
    print, '.', STRCOMPRESS( ((theChildrenList->Item(j))->GetNodeValue()) , REMOVE_ALL=1 )
    if (STRJOIN(STRSPLIT(STRCOMPRESS( ((theChildrenList->Item(j))->GetNodeValue()) ,/REMOVE_ALL ),'\n'),'') EQ '') then begin
      nullvoid=theObject->RemoveChild(theChildrenList->Item(j))
      print, 'removed'
      endif
    endif
  nullvoid=DOM_trimwhitespaces(theChildrenList->Item(j), level+1)
  endfor
return, theObject
end

function erase_attributes, object, attributes

if (object->GetNodeType() ne 1) then return,1 
for jattr=0, n_elements(attributes)-1 do begin
  object->RemoveAttribute, attributes[jattr]  
endfor
children=object->GetChildNodes()
for jchild=0, children->GetLength()-1 do begin
  err=erase_attributes(children->item(jchild),attributes)
endfor

return, 1

end

pro xtsm_parse, verbose=vb

  StartParseTime=SYSTIME(1)
  parsetimecheck=[SYSTIME(1)]
  parsetimelabels=['total parse time']

  xtsmstring=SCOPE_VARFETCH('ACTIVE_XTSM', LEVEL=1)
  oDocument=open_xml_from_string(xtsmstring)
  
  COMMON global_variables, shotnumber
  oData = oDocument->GetFirstChild()
  
  ;erase existing parser errors and current values here
  err=erase_attributes((oDocument->GetElementsByTagName('XTSM'))->item(0),['currentvalue','parseerror']) 
  
  ;retrieve the next shot number from main level; if it does not exist, set it to zero
  mainlevelvars=SCOPE_VARNAME(LEVEL=1)
  if (where(mainlevelvars eq 'NEXT_SHOTNUMBER') ne -1) then shotnumber=SCOPE_VARFETCH('next_shotnumber', LEVEL=1) else begin
    shotnumber=0
    (SCOPE_VARFETCH('NEXT_SHOTNUMBER', LEVEL=1, /ENTER)) = shotnumber
  endelse

  
  ;gets first Seq. Selector Statement, and executes it literally, expecting it to define the variable 'sequence'
  SequenceSelectorNode = (oData->GetElementsByTagName('SequenceSelector'))->Item(0)  
  SStext=(SequenceSelectorNode->GetFirstChild())
  err=execute(SStext->getNodeValue())
  if (keyword_set(vb)) then print, "Loading the sequence named: " + sequence

  ;below we isolate the active sequence node
  bodyData=(oData->GetElementsByTagName('body'))->Item(0)
  oseqs_list=bodyData->GetElementsByTagName('Sequence')
  for activeseq=0, (oseqs_list->GetLength()-1) do if (((((oseqs_list->item(activeseq))->GetElementsByTagName('Name'))->Item(0))->GetFirstChild())->GetNodeValue() EQ sequence) then break
  aseq_node=oseqs_list->item(activeseq)

  ;Need to locate and tag all variables
  ;locate parameters in head and execute declarations
  ;note: simple execute calls for parameter evaluation take O(10us) per evaluation.
  headData=(oData->GetElementsByTagName('head'))->Item(0)
  oparam_list=headData->GetElementsByTagName('Parameter')
  head_param_decl=''
  for j=0, (oparam_list->GetLength())-1 do err=execute(((((oparam_list->item(j))->GetElementsByTagName('Name'))->item(0))->GetFirstChild())->GetNodeValue()+'='+((((oparam_list->item(j))->GetElementsByTagName('Value'))->item(0))->GetFirstChild())->GetNodeValue())
  
  edgearray=[[0,0,0,0,0],[0,0,0,0,0]]    ; an array to hold edge data: timing group, timing group index, time, value, lookup index for uid of generating element in uidlist
  uidlist=['parser_generated']
  intervalarray=[[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]     ;an array to hold interval data: timing group, timing group index, starttime, endtime, voltage resolution, time resolution, lookup index for value formula in intervaldefns, index of uid in uidlist
  intervaldefns=!NULL   ; an array of strings holding interval value definitions

  parsetimecheck=[parsetimecheck,SYSTIME(1)]
  parsetimelabels=[parsetimelabels,'setup complete']

  ;;;;;;;;;;;;;;;;;;;;;;;;;;;;
  ;fill the arrays above by parsing the sequence
  err=parseSequence(aseq_node,(headData->GetElementsByTagName('ChannelMap'))->item(0), edgearray, intervalarray, intervaldefns, uidlist)

  parsetimecheck=[parsetimecheck,SYSTIME(1)]
  parsetimelabels=[parsetimelabels,'first parse complete']

  edgesexist=1
  intervalsexist=1
  ;strip off artificial edges and intervals
  if ((size(edgearray))[2] gt 2) then edgearray=edgearray[*,2:*] else edgesexist=0 
  if ((size(intervalarray))[2] gt 2) then intervalarray=intervalarray[*,1:-2] else intervalsexist=0 
  ;locate the final time edge
  if (intervalsexist) then lasttime=max([reform(edgearray[2,*]),reform(intervalarray[2,*]),reform(intervalarray[3,*])]) else lasttime=max([reform(edgearray[2,*])])
  
  ; find the sequence's end time specification 
   seqendtime=float(GETNODEVALUE_ORDEFAULT(aseq_node,'EndTime',lasttime))
   if (seqendtime gt 100000.) then begin 
      seqendtime=100000.
      ((aseq_node->GetElementsByTagName('EndTime'))->item(0))->SetAttribute, "parseerror", "Coerced to maximum 100000ms experiment time"
   endif
   if (seqendtime le 0.) then begin 
      seqendtime=10000.
      if ((aseq_node->GetElementsByTagName('EndTime'))->GetLength() ge 1) then ((aseq_node->GetElementsByTagName('EndTime'))->item(0))->SetAttribute, "parseerror", "Set to default 10000ms experiment time"
   endif

  ; ADD ERROR-TRAPPING TO FLAG EDGES / INTERVALS WHO EXCEED SEQUENCE'S ENDTIME!!!!
   lasttime=seqendtime


  ; NOW process the edges and intervals into a set of sparse control arrays, one for each timing group:
  ; 1) find all edge or interval requested timing groups.
  ; 2) find all channel-map defined timing groups
  ; 3) error-trap and inform of edges or intervals which will not be processed
  ; 4) establish clocking relations between channel-map defined groups 
  ; 5) for each group, break intervals/edges in each timing group into perfect overlaps & find compromise timings
  reqtiminggroups=!NULL
  edgetiminggroups=edgearray[0,uniq(edgearray[0,*],sort(edgearray[0,*]))]
  reqtiminggroups=[[edgetiminggroups],reqtiminggroups]
  if (intervalsexist) then begin
    intervaltiminggroups=intervalarray[0,uniq(intervalarray[0,*],sort(intervalarray[0,*]))]
    reqtiminggroups=[[intervaltiminggroups],reform(reqtiminggroups)]
    endif
  ;timinggroups=([[intervaltiminggroups],[edgetiminggroups]])[uniq([[intervaltiminggroups],[edgetiminggroups]],sort([[intervaltiminggroups],[edgetiminggroups]]))]
  reqtiminggroups=reqtiminggroups[uniq(reqtiminggroups,sort(reqtiminggroups))]
  
  ;get all timing group data
  timinggroupdata=((headData->GetElementsByTagName('ChannelMap'))->item(0))->GetElementsByTagName('TimingGroupData')
  
    clocksources=!NULL  ;this array holds labels the physical clock channel each element of the timingstring should end up on
    clockchanges=!NULL  ;this array holds all times at which the clock channel should change its value
    selfclockers=!NULL  ;this array keeps track of all timinggroups which are self-clocking
    timinggroupnames=!NULL
    
  ;need to create a heirarchical list of timing-groups, starting with those who clock nothing, then those who clock something that clocks nothing,
  ;then those who clock something that clocks something that clocks nothing...
  timinggroupclocklevel=bytarr(timinggroupdata->getlength())
    bumpcount=1
    while (bumpcount ne 0) do begin
      maxlevel=max(timinggroupclocklevel)
      if (maxlevel gt (timinggroupdata->getlength())) then err=errorflag('timing group clocking loops are not permitted - check <TimingGroupData> nodes for circular <ClockedBy> references')
      bumpcount=0
      for s=0,(timinggroupdata->getlength()-1) do begin
        if (((timinggroupdata->item(s))->GetElementsByTagName('GroupNumber'))->GetLength() gt 0) then gn=fix(((((timinggroupdata->item(s))->GetElementsByTagName('GroupNumber'))->item(0))->GetFirstChild())->GetNodeValue()) else err=errorflag('All timing groups must have groupnumbers; offending <TimingGroupData> node has position '+s+' in channelmap')
        if (maxlevel eq 0) then timinggroupnames=[timinggroupnames,gn]
        if (timinggroupclocklevel[s] eq maxlevel) then begin
          if (((timinggroupdata->item(s))->GetElementsByTagName('ClockedBy'))->GetLength() gt 0) then clocksource=((((timinggroupdata->item(s))->GetElementsByTagName('ClockedBy'))->item(0))->GetFirstChild())->GetNodeValue() else err=errorflag('TimingGroup '+gn+' must have a channel as clock source (<ClockedBy> node)')
          if (clocksource ne 'self') then begin 
            clockgroup=((((getChannel((headData->GetElementsByTagName('ChannelMap'))->item(0),clocksource))->GetElementsByTagName('TimingGroup'))->item(0))->GetFirstChild())->GetNodeValue() 
            for k=0,(timinggroupdata->getlength()-1) do if (((((timinggroupdata->item(k))->GetElementsByTagName('GroupNumber'))->item(0))->GetFirstChild())->GetNodeValue() eq clockgroup) then break
            timinggroupclocklevel[k]=maxlevel+1
            bumpcount+=1
          endif
        endif
      endfor
    endwhile
    
    ;now we want to establish clocking resolutions which work for each clocking chain, such that descendents clock at a multiple of their clocker's base frequency
    cl=max(timinggroupclocklevel)
    while (cl ge 0) do begin
      tgroupsthislevel=timinggroupnames[where(timinggroupclocklevel eq cl)]
      for s=0, n_elements(tgroupsthislevel)-1 do begin
        ;find the corresponding data node
        for k=0,(timinggroupdata->getlength()-1) do if (((((timinggroupdata->item(k))->GetElementsByTagName('GroupNumber'))->item(0))->GetFirstChild())->GetNodeValue() eq tgroupsthislevel[s]) then break
        ;get the requested time resolution - if self-clocked accept it exactly and continue
        clockperiod=GetNodeValue_orDefault(timinggroupdata->item(k),'SelfClockPeriod',GetNodeValue_orDefault(timinggroupdata->item(k),'ClockPeriod','0.0002'))
        
        ; if this timinggroup has no clockperiod node in its data node, append one - otherwise try to read its current_value attribute; use it if it exists
        if (((timinggroupdata->item(k))->GetElementsByTagName('ClockPeriod'))->GetLength() eq 0) then begin
          newnode=(timinggroupdata->item(k))->AppendChild(((timinggroupdata->item(k))->GetOwnerDocument())->CreateElement('ClockPeriod'))
          temp=newnode->AppendChild((newnode->GetOwnerDocument())->CreateTextNode( '0.0002'))
          endif
        if (((((timinggroupdata->item(k))->GetElementsByTagName('ClockPeriod'))->item(0))->GetAttribute('current_value')) ne '') then clockperiod=(((timinggroupdata->item(k))->GetElementsByTagName('ClockPeriod'))->item(0))->GetAttribute('current_value')
        ;get the clocker's set time resolution, find the closest greater multiple of the clocker's resolution, and set this group's resolution
        if (((((timinggroupdata->item(k))->GetElementsByTagName('ClockedBy'))->item(0))->GetFirstChild())->GetNodeValue() ne 'self') then begin 
          ;find the clocker's data
          clocksource=((((timinggroupdata->item(k))->GetElementsByTagName('ClockedBy'))->item(0))->GetFirstChild())->GetNodeValue()
          clockgroup=((((getChannel((headData->GetElementsByTagName('ChannelMap'))->item(0),clocksource))->GetElementsByTagName('TimingGroup'))->item(0))->GetFirstChild())->GetNodeValue() 
          for m=0,(timinggroupdata->getlength()-1) do if (((((timinggroupdata->item(m))->GetElementsByTagName('GroupNumber'))->item(0))->GetFirstChild())->GetNodeValue() eq clockgroup) then break
          timerperiod=GetNodeValue_orDefault(timinggroupdata->item(m),'SelfClockPeriod',GetNodeValue_orDefault(timinggroupdata->item(m),'ClockPeriod','0.0002'))
          ; take the clock group's clock period from its timinggroupdata->clockperiod node's current_value attribute - if it exists 
          if (((((timinggroupdata->item(m))->GetElementsByTagName('ClockPeriod'))->item(0))->GetAttribute('current_value')) ne '') then timerperiod=(((timinggroupdata->item(m))->GetElementsByTagName('ClockPeriod'))->item(0))->GetAttribute('current_value')          
          ; coerce the clock period to be the smallest multiple of its source's clock period 
          clockperiod=ceil(double(clockperiod)/double(timerperiod))*double(timerperiod)
        endif
        ; having made a decision on this group's timing resolution, append it as the current_value attribute on the clockperiod node  
        ((((timinggroupdata->item(k))->GetElementsByTagName('ClockPeriod'))->item(0)))->SetAttribute, 'current_value', strtrim(string(clockperiod),1)
      endfor
      cl-=1
    endwhile
    

    timinggroups=timinggroupnames[sort(timinggroupclocklevel)]
    timinggroupclocklevel=timinggroupclocklevel[sort(timinggroupclocklevel)]
    ; error-flag edges / intervals on timing-groups that will not be processed
    foreach reqtiminggroup, reqtiminggroups do begin
       if (where(timinggroups eq reqtiminggroup) eq -1) then begin
          ; find all edges, intervals and channels on that group
          ; FINISH THIS ERROR-TRAPPING ROUTINE
       endif
    endforeach
   
  parsetimecheck=[parsetimecheck,SYSTIME(1)]
  parsetimelabels=[parsetimelabels,'timing group relations determined']
  
  ; export timinggroup relations and clocking data for hardware emulation
  emulationmatrix=!null
  
  
  for f=0,n_elements(timinggroups)-1 do begin
    tg=timinggroups[f]
    for k=0,(timinggroupdata->getlength()-1) do if (((((timinggroupdata->item(k))->GetElementsByTagName('GroupNumber'))->item(0))->GetFirstChild())->GetNodeValue() eq tg) then break
    if (((timinggroupdata->item(k))->GetElementsByTagName('DelayTrain'))->GetLength() ge 1) then dt=1 else dt=0
    clocksource=((((timinggroupdata->item(k))->GetElementsByTagName('ClockedBy'))->item(0))->GetFirstChild())->GetNodeValue()
    cpd=((((timinggroupdata->item(k))->GetElementsByTagName('ClockPeriod'))->item(0)))->GetAttribute('current_value')
    numchan=((((timinggroupdata->item(k))->GetElementsByTagName('ChannelCount'))->item(0))->GetFirstChild())->GetNodeValue()
    if (clocksource ne 'self') then begin
      clockgroup=((((getChannel((headData->GetElementsByTagName('ChannelMap'))->item(0),clocksource))->GetElementsByTagName('TimingGroup'))->item(0))->GetFirstChild())->GetNodeValue()
      clockchannel=((((getChannel((headData->GetElementsByTagName('ChannelMap'))->item(0),clocksource))->GetElementsByTagName('TimingGroupIndex'))->item(0))->GetFirstChild())->GetNodeValue()
    endif else begin
      clockgroup=-1
      clockchannel=-1
    endelse
    emulationmatrix=[[emulationmatrix],[timinggroups[f],timinggroupclocklevel[f],fix(clockgroup),fix(clockchannel),0,dt,float(cpd),float(numchan)]]
  endfor
  emulationmatrix=emulationmatrix[*,reverse(sort(reform(emulationmatrix[1,*])))]
  (SCOPE_VARFETCH('active_emulationmatrix', LEVEL=1, /ENTER))=emulationmatrix
  
  ;break intervals and edges into timing groups, loop through all groups, creating control data
  ;running them in ascending order by clocklevel will assure the clockstrings are ready when needed
  ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
  
  foreach timinggroup, timinggroups do begin
    ;first locate the timinggroupdata node
    for j=0,(timinggroupdata->getlength()-1) do if (((((timinggroupdata->item(j))->GetElementsByTagName('GroupNumber'))->item(0))->GetFirstChild())->GetNodeValue() eq timinggroup) then break
    if (j eq timinggroupdata->getlength()) then err=errorflag('timing group has no data')
    ;then find its clocksource group, groupdata, clock channel number, clock's (parent) resolution
    clocksource=((((timinggroupdata->item(j))->GetElementsByTagName('ClockedBy'))->item(0))->GetFirstChild())->GetNodeValue() ; clocksource for the current channel (the string labeling the channel)
    clockchannelname=clocksource
    ResolutionBits=((((timinggroupdata->item(j))->GetElementsByTagName('ResolutionBits'))->item(0))->GetFirstChild())->GetNodeValue()
    if (clocksource ne 'self') then begin
      clocksource=getChannel((headData->GetElementsByTagName('ChannelMap'))->item(0),clocksource) ;clocksource as channel DOM object
      clocktiminggroup=getNodeValue_orDefault(clocksource,'TimingGroup',0)
      clocktiminggroupindex=getNodeValue_orDefault(clocksource,'TimingGroupIndex',0)
      for k=0,(timinggroupdata->getlength()-1) do if (((((timinggroupdata->item(k))->GetElementsByTagName('GroupNumber'))->item(0))->GetFirstChild())->GetNodeValue() eq clocktiminggroup) then break
      if (((timinggroupdata->item(k))->GetElementsByTagName('ClockPeriod'))->GetLength() gt 0) then parentgenresolution=((((timinggroupdata->item(k))->GetElementsByTagName('ClockPeriod'))->item(0)))->GetAttribute('current_value')
      if (((timinggroupdata->item(k))->GetElementsByTagName('DelayTrain'))->GetLength() eq 0) then bytesperrepeat=4 else bytesperrepeat=0
      if (ResolutionBits eq 1) then bytesperrepeat=0 ; any digital group which is not self clocking, will not hold repeats
    endif
    ;get biographical data about the timing group itself: number of channels, its clock period 
    if (((timinggroupdata->item(j))->GetElementsByTagName('ChannelCount'))->GetLength() ge 1) then numchan=((((timinggroupdata->item(j))->GetElementsByTagName('ChannelCount'))->item(0))->GetFirstChild())->GetNodeValue() else numchan=8
    if (((timinggroupdata->item(j))->GetElementsByTagName('ClockPeriod'))->GetLength() ge 1) then clockgenresolution=(((timinggroupdata->item(j))->GetElementsByTagName('ClockPeriod'))->item(0))->GetAttribute('current_value') else clockgenresolution=0.0002D
    numchan=fix(numchan)
    timinggroupname=getNodeValue_orDefault(timinggroupdata->item(j),'Name','TimingGroup_'+string(timinggroup))
    scale=((((timinggroupdata->item(j))->GetElementsByTagName('Scale'))->item(0))->GetFirstChild())->GetNodeValue()
    bytespervalue=ceil(ResolutionBits/8.) ;number of bytes to represent output values by in timingstring
    if (bytesperrepeat eq !null) then bytesperrepeat=4 ;number of bytes to represent time values by in timingstring
    groupedges=edgearray[*,where(edgearray[0,*] eq timinggroup,/NULL)]
    groupintervals=intervalarray[*,where(intervalarray[0,*] eq timinggroup,/NULL)]
    
    ;coerce all times to a multiple of the _parent_ clock cycle (using the parent's resolution allows us to subresolution step.)
    if (groupedges ne !null) then groupedges[2,*]=double(round(groupedges[2,*]/parentgenresolution))*parentgenresolution
    if (groupintervals ne !null) then groupintervals[2,*]=double(round(groupintervals[2,*]/parentgenresolution))*parentgenresolution
    if (groupintervals ne !null) then groupintervals[3,*]=double(round(groupintervals[3,*]/parentgenresolution))*parentgenresolution
    lasttimecoerced=float(ceil(seqendtime/clockgenresolution,/L64))*clockgenresolution
    ; assemble all times at an edge or start or end of an interval, sort them
    alltimes=[0,lasttimecoerced]
    if (groupedges ne !null) then alltimes=[alltimes,reform(groupedges[2,*])]
    if (groupintervals ne !null) then alltimes=[alltimes,reform(groupintervals[2,*]),reform(groupintervals[3,*])] 
    if (alltimes ne !null) then alltimes=alltimes[uniq(alltimes,sort(alltimes))]
    denseT=!NULL  ; create a variable to hold all update times for this timing group 
    ;start a loop over all intervals between these times, generate update times 
    for time=0,n_elements(alltimes)-1 do begin
      ;find all intervals (on this group! this was looking at all intervals on all groups before?!) which are active in this window
      if (groupintervals ne !null) then activeintervals=groupintervals[*,where((groupintervals[2,*] le alltimes[time]) and (groupintervals[3,*] gt alltimes[time]),/null)] else activeintervals=!null
      ;if there are any, generate necessary time edges 
      if (activeintervals ne !NULL) then begin 
        if ((size(activeintervals))[0] gt 1) then numact=(size(activeintervals))[2] else numact=1
        ;find a compromise resolution (smallest, coerced to a multiple of the group's clocking resolution)
        res=double(ceil(min(activeintervals[5,*])/clockgenresolution))*clockgenresolution
        ;define the times in this window using universal time
        T=DINDGEN(((alltimes[time+1]-alltimes[time])/res))*res + alltimes[time]
        ;add these times to a list of all times for this timing group
        denseT=[[denseT],T]
        endif else denseT=[[denseT],alltimes[time]]
    endfor
    ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
    ;send this timing information back into parser to re-evaluate all intervals, turning them into edges
    ;this is the 'harvest-pass'
    ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
    
    if (((size(groupedges))[0] ne 2) or ((size(groupedges))[0] lt 2)) then groupedges=[[0,-1,0,0,0.],[0,-1,0,0,0.]]
    if (((size(groupintervals))[0] ne 2) or ((size(groupintervals))[0] lt 2)) then groupintervals=[[0,0,0,0,0,0,0,0.],[0,0,0,0,0,0,0,0.]] 
    
    err=parseSequence(aseq_node,(headData->GetElementsByTagName('ChannelMap'))->item(0), groupedges, groupintervals, intervaldefns, uidlist, HARVEST_INTERVAL_TIMING_GROUP=timinggroup, HARVEST_TIMES=denseT)
    ;now we start building the timing strings - strategy is to build val, rep pairs for all updates on all channels whose output resolution is greater than one bit. 
    ; For one-bit groups, we need only record the times at which the channel's output should be flipped
    ;find total number of update strobes needed on this timing group
    finalind=long(max([reform(groupedges[0,*]),0L]))+1       ;;;;;;;;;;;THIS IS A POTENTIAL PROBLEM LINE
    initialword=!null
    finalword=!null
    ;initialize the sparse update string
    ;this array will hold the sparse timing array to be exploded into full control array by the PXI system 
    timingstring=[byte(uint(numchan),0,1),byte(bytespervalue,0,1),byte(bytesperrepeat,0,1),byte(n_elements(denset),0,4)]  ;,byte(finalind+1,0,4)   
    
    ;the next starts a loop over all channels in this group, indexed by k
    ;;;;;;;;;;;;;;;;;;;;;;;;;;;
    for k=0, numchan-1 do begin
      ;get channel data for initial and hold values; assemble final word from bits
      channel=getChannelbyIndex((headData->GetElementsByTagName('ChannelMap'))->item(0),k,timinggroup)
      ;check if this channel is already claimed as a clock for any other group
      isclock=-1
      if (clocksources ne !NULL) then isclock=where((clocksources[1,*] eq timinggroup) and (clocksources[2,*] eq k))

      initval=getNodeValue_orDefault(channel,'InitialValue',0)
      finval=getNodeValue_orDefault(channel,'HoldingValue',0)
      if (isclock ne -1) then begin & initval=1 & finval=0 & endif
      if (ResolutionBits eq 1) then begin
        finalword=[finalword,fix(finval) ge 0.5]
        initialword=[initialword,fix(initval) ge 0.5]
      endif
      ; if it is a clock, append the corresponding timing string and continue to next loop iteration 
      if (isclock ne -1) then begin 
        clockchangesindices=[where(clockchanges eq 0,/null),n_elements(clockchanges)]
        denset=[denset,clockchanges[clockchangesindices[isclock]:(clockchangesindices[isclock+1]-1)]*double(clockgenresolution)]
        denset=denset[uniq(denset,sort(denset))]
        if (ResolutionBits eq 1) then timingstring=[timingstring,clockchanges[clockchangesindices[isclock]:(clockchangesindices[isclock+1]-1)]] else err=errorflag("non-digital clocking signals are not permitted") 
        continue 
      endif
      ;select edges on this channel, if there are any
      edgesbychannel=groupedges[*,where(groupedges[1,*] eq k, /null)]
      ;if there are no edges, add initial and final values
      
      if (edgesbychannel eq !null) then edgesbychannel=[[0,k,0,initval,0],[finalind,k,0,finval,0]]
      ; if no first edge, add one, using initial val specified in channel data
      if (edgesbychannel[0,0] ne 0) then edgesbychannel=[[0,k,0,initval,0],[reform(edgesbychannel,5,n_elements(edgesbychannel)/5)]]
      ; if no final edge, add one
      if (edgesbychannel[0,-1] ne finalind) then edgesbychannel=[[reform(edgesbychannel,5,n_elements(edgesbychannel)/5)],[finalind,k,0,finval,0]]
      ; create an array representing number of times to repeat each element in the final control array
      times=ulong(edgesbychannel[0,*])
      
      ; analog channels algorithm:
      if (ResolutionBits ne 1) then begin
        
        ; create a byte array of values using appropriate number of bytes for channel resolution
        updates=byte(UINT((edgesbychannel[3,*]/scale+0.5)*2.^ResolutionBits),0,bytespervalue*n_elements(edgesbychannel[2,*]))
        ; reform this into an array of rows, each with byte representation of update value as LSB...MSB
        updates=reform(updates,bytespervalue,n_elements(updates)/bytespervalue)
        ; determine how many updates this value should be repeated over
        repeats=[(times-shift(times,1))[1:*],1]  ;;SHOULD THE FINAL REPEAT VALUE BE 1 OR ZERO?????? !!
        ; express that in a four-bit integer, reform this into an array of rows, each with byte representation of update value as LSB...MSB
        repeats=reform(byte(repeats,0,bytesperrepeat*n_elements(repeats)),bytesperrepeat,n_elements(repeats))
        ; append the timing string for this channel - first 4 bytes express length, in bytes, of the string.  rest of string is elements: (value (bytespervalue long in bytes), number of sample to repeat this value (bytesperrepeat long in bytes) ) 
        timingstring=[timingstring,byte((bytespervalue+bytesperrepeat)*n_elements(times),0,4),reform([updates,repeats],(bytespervalue+bytesperrepeat)*n_elements(times))]
      endif
      ; digital channels algorithm:
      if (ResolutionBits eq 1) then begin
;        finval=getNodeValue_orDefault(channel,'HoldingValue',0)
;        finalword=[finalword,fix(finval) ge 0.5]
        ; sort by time, threshhold values to zero and one if greater or equal to 0.5
        edgesbychannel=edgesbychannel[*,sort(edgesbychannel[0,*])]
        edgesbychannel[3,*]=edgesbychannel[3,*] ge 0.5
        ; remove repeated values - problem: the function uniq() has a wrap-around behavior - if last edge is same as first, it is discarded, so we use an if-statement to retain it
        if (edgesbychannel[3,-1] ne edgesbychannel[3,0]) then edgesbychannel=edgesbychannel[*,uniq(edgesbychannel[3,*])] else edgesbychannel=[[edgesbychannel[*,uniq(edgesbychannel[3,*])]],[edgesbychannel[*,-1]]]        
        ; in the trivial case that there are only two edges, and they are the same, remove one
        if (((size(edgesbychannel))[2] eq 2) and (edgesbychannel[3,1] eq edgesbychannel[3,0])) then edgesbychannel=edgesbychannel[*,0]
        ; create the timing string and append it - timing string should be a list of state change times (times rep. as clock-cycles)
        timingstring=[timingstring,ulong(reform(edgesbychannel[2,*])/clockgenresolution)]
      endif
    endfor
    
    if (ResolutionBits ne 1) then begin
      ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
      ; this handles timinggroup data for a non-digital output set
      ; save the timingstring and timingdata in the global scope
      (SCOPE_VARFETCH('active_timingstring_'+string(timinggroup,format='(I03)'), LEVEL=1, /ENTER)) = [byte(ulong64(8UL+n_elements(timingstring)),0,8),timingstring]
      (SCOPE_VARFETCH('active_timingdata_'+string(timinggroup,format='(I03)'), LEVEL=1, /ENTER)) = [1B,byte(fix(timinggroup)-1),0B,byte(ulong(1./clockgenresolution),0,4),0B,1B,bytarr(7),byte(timinggroupname),bytarr(24-strlen(timinggroupname)),byte(clockchannelname),bytarr(24-strlen(clockchannelname))] ; this codes the board as analog output, device index equal to group number, clock source indexed by group number, clock frequency set to 1/clockrate, whose start does not trigger the sequence, and which needs sparse to dense conversion
    endif else begin
      ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
      ; this handles the timinggroup data for a digital output set. 
      if (((timinggroupdata->item(j))->GetElementsByTagName('DelayTrain'))->GetLength() ge 1) then begin
      ; this handles _delaytrain_ clocking outputs - first break out the fragments corresponding to each channel
        
        timingstring=timingstring[7:*]
        pointers=[where(timingstring eq 0),n_elements(timinstring)]
        clockstring=!null
        clockstringheader=[byte(n_elements(pointers)-1),0B,4B]
        maxups=0
        for s=0, n_elements(pointers)-2 do begin
          
          timingstringfrag=timingstring[pointers[s]:(pointers[s+1]-1)]
         ; now extract only the risetimes from each timingstring fragment, then form differences between neighboring elements
          clockstringfrag=[0,(timingstringfrag[0:*:2]-shift(timingstringfrag[0:*:2],1))[1:*]]
          clockstring=[clockstring,byte(4*(1L+n_elements(timingstringfrag)/2L),0,4),byte(clockstringfrag,0,4*n_elements(clockstringfrag))]
          ;clockstringheader=[clockstringheader,byte(n_elements(timingstringfrag)/2,0,4)]
          maxups=max([maxups,n_elements(clockstringfrag)])
        endfor
        ;clockstring=[clockstringheader,byte(clockstring,0,4*n_elements(clockstring))]
        clockstring=[byte(ulong64(n_elements(clockstringheader)+n_elements(clockstring)+12),0,8),clockstringheader,byte(long(maxups),0,4),clockstring]
        (SCOPE_VARFETCH('active_timingdata_'+string(timinggroup,format='(I03)'), LEVEL=1, /ENTER)) = [4B,4B,0B,byte(ulong(80000000),0,4),1B,0B,bytarr(7),byte(timinggroupname),bytarr(24-strlen(timinggroupname)),byte(clockchannelname),bytarr(24-strlen(clockchannelname))] ; this codes the board as delaytrain, RIO01 delay, self-clocked, at 80MHz, whose start triggers the sequence, and which doesn't need sparse to dense control array expansion
        ;NOTE THE INEFFICIENCY HERE - THERE WOULD BE NO NEED TO INSERT FALL TIMES FOR THESE DELAYTRAIN STRINGS IN THE CLOCK-STRING FORMATION!! (~LINE 819)
      endif else begin
      ; this is for standard dio output
      ; first convert the concatenated timingstrings of update times for each channel into an array of numchan-bit integers, with a repeat count
        
        timingstring=timingstring[7:*]
        bytesperentry=(bytesperrepeat+ceil(numchan/8.))  ;calculate the length of the control string
        clockstring=BYTARR(n_elements(uniq(timingstring,sort(timingstring)))*bytesperentry,/nozero)  ; create a string into which to write the data
        ;create pointers to reference the timingstring array where each channel starts (at zero time edge)
        pointers=where(timingstring eq 0)
        origpointers=pointers
        ;create an initialization byte and mapping to integer
        ;thisbyte=ulong(bytarr(n_elements(pointers)));+1
        thisbyte=(initialword+1) mod 2
        binaryconverter=ulong(2)^INDGEN(n_elements(pointers), /ULONG)
        entries=long(0)
        lasttime=ulong(0)
        nexttime=ulong(0)
        if (bytesperrepeat ne 0) then begin
          ; this is the algorithm for standard sparse array
          while(pointers[0] ne origpointers[1]) do begin
            ; the following identifies which elements of thisbyte need to be flipped (those whose corresponding pointer ties for minimum time in timingstring)
            thistime=nexttime
            flips=where(timingstring[pointers] eq thistime) 
            ;flip those bits
            thisbyte[flips]=(thisbyte[flips]+1) mod 2
            ;advance the pointers where active
            pointers[flips]++
            nexttime=min((timingstring[pointers])[where(timingstring[pointers] ne 0)])          ;used to be min(timingstring[pointers]), but need to forbid pointers from wrapping into next set
            ;convert the byte array into a binary 32-bit integer (ulong) and append to the clock control string
            clockstring[entries*bytesperentry:((entries+1)*bytesperentry-1)]=[byte(total(thisbyte*binaryconverter,/integer),0,ceil(numchan/8.)),byte(ulong(nexttime-thistime),0,bytesperrepeat)]  
            entries++
          endwhile
        endif else begin
          ; this is the algorithm for control array for a group clocked by a delay train (one which has 0 bytes per repeat)
          
          while(pointers[0] ne origpointers[1]) do begin
            ; the following identifies which elements of thisbyte need to be flipped (those whose corresponding pointer ties for minimum time in timingstring)
            thistime=nexttime
            flips=where(timingstring[pointers] eq thistime) 
            ;flip those bits
            thisbyte[flips]=(thisbyte[flips]+1) mod 2
            ;advance the pointers where active
            pointers[flips]++
            nexttime=min((timingstring[pointers])[where(timingstring[pointers] ne 0)])          ;used to be min(timingstring[pointers]), but need to forbid pointers from wrapping into next set
            ;convert the byte array into a binary 32-bit integer (ulong) and append to the clock control string
            clockstring[entries*bytesperentry:((entries+1)*bytesperentry-1)]=[byte(total(thisbyte*binaryconverter,/integer),0,ceil(numchan/8.))]  
            entries++
          endwhile
        endelse
        
        parsetimecheck=[parsetimecheck,SYSTIME(1)]
        parsetimelabels=[parsetimelabels,'timing group '+string(timinggroup, format="(I02)")+' boolean sparse array to integer sparse array conversion complete']
        ;need to append the last value, which is the word-representation of the holding values of all channels 
        finalword=ulong64(total(finalword*2ULL^UL64INDGEN(numchan)))
        if (bytesperrepeat ne 0) then clockstring[-(ceil(numchan/8.)+bytesperrepeat):*]=[byte(finalword,0,ceil(numchan/8.)),byte(ulong(1),0,bytesperrepeat)] else clockstring[-(ceil(numchan/8.)+bytesperrepeat):*]=[byte(finalword,0,ceil(numchan/8.))]
        ;prepend the structural information and save in global scope
        
        finalclockingindices=clockchanges[-1]
        if (n_elements(clockchangesindices) gt 1) then finalclockingindices=[finalclockingindices,clockchanges[clockchangesindices[1:*]-1]]
        finalind=max([reform(groupedges[0,*]),finalclockingindices])
        finaltime=max([reform(groupedges[2,*])/clockgenresolution,finalclockingindices])*clockgenresolution
        
        if (bytesperrepeat ne 0 ) then begin
          clockstring=[byte(ulong64(n_elements(clockstring)+19ULL),0,8),byte(1,0,1),byte(ceil(numchan/8.),0,1),byte(bytesperrepeat,0,1),byte(ulong(finaltime/clockgenresolution),0,4),byte(ulong(n_elements(clockstring)),0,4),clockstring]
          (SCOPE_VARFETCH('active_timingdata_'+string(timinggroup,format='(I03)'), LEVEL=1, /ENTER)) = [0B,0B,0B,byte(ulong(5000000),0,4),0B,1B,bytarr(7),byte(timinggroupname),bytarr(24-strlen(timinggroupname)),byte(clockchannelname),bytarr(24-strlen(clockchannelname))] ; this codes the board as digital output, PXI1Slot2/port0:3, self-clocked, at 5MHz, whose start doesn't trigger the sequence, and which needs sparse to dense control array expansion
        endif
        if (bytesperrepeat eq 0 ) then begin
          clockstring=[byte(ulong64(n_elements(clockstring)+19ULL),0,8),byte(1,0,1),byte(ceil(numchan/8.),0,1),byte(bytesperrepeat,0,1),byte(ulong(entries),0,4),byte(ulong(n_elements(clockstring)),0,4),clockstring]
          (SCOPE_VARFETCH('active_timingdata_'+string(timinggroup,format='(I03)'), LEVEL=1, /ENTER)) = [0B,0B,0B,byte(ulong(5000000),0,4),0B,0B,bytarr(7),byte(timinggroupname),bytarr(24-strlen(timinggroupname)),byte(clockchannelname),bytarr(24-strlen(clockchannelname))] ; this codes the board as digital output, PXI1Slot2/port0:3, self-clocked, at 5MHz, whose start doesn't trigger the sequence, and which doesn't need sparse to dense control array expansion
        endif
      endelse
      (SCOPE_VARFETCH('active_timingstring_'+string(timinggroup,format='(I03)'), LEVEL=1, /ENTER)) = clockstring
    endelse
   ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
   ; this handles the clocking data for this timing group - idea is store the clocking update times for this group to be retrieved when the clocking 
   ; channel's group is processed (gauranteed to be a later loop iteration by establishing the timinggroup heirachy above)
   ; now create the clocking pulse train for this timing group
    parsetimecheck=[parsetimecheck,SYSTIME(1)]
    
    parsetimelabels=[parsetimelabels,'timing group '+string(timinggroup, format="(I02)")+' channels processed']
    if (parentgenresolution eq !null) then clockrisetimes=ulong(denset/clockgenresolution) else clockrisetimes=ulong(denset/parentgenresolution); using 32-bit long integer limits cycle length to 860s at 200ns clock generator resolution    if (clockrisetimes[0] ne 0) then clockrisetimes=[0,clockrisetimes] ; ensure it has a zero-time rise
    
    clockfalltimes= ((clockrisetimes+shift(clockrisetimes,-1))/2) ;put fall times equidistant from neighboring rises
    clockfalltimes[-1]=clockrisetimes[-1]+2
    clockchangestartindex=n_elements(clockchanges)
    ; next line interleaves rises and falls     
    clockchanges=[clockchanges,(reform(transpose([[clockrisetimes],[clockfalltimes]]),2*n_elements(clockfalltimes)))[0:-1]] ; form this into a one-dimensional array of times (rep by clock cycle count) the state of this clock channel should be changed, append to all other channels (we will separate them back later)

    clockchangeendindex=n_elements(clockchanges)-1
    clocksources=[[clocksources],[timinggroup,clocktiminggroup,clocktiminggroupindex,clockchangestartindex,clockchangeendindex]] ; record the timinggroup indices, and start/end of corresponding clockchanges fragment
    parsetimecheck=[parsetimecheck,SYSTIME(1)]
    parsetimelabels=[parsetimelabels,'timing group '+string(timinggroup, format="(I02)")+' fully processed']
    
  endforeach
  
  if (keyword_set(vb)) then print, "Timing:"
  if (keyword_set(vb)) then print, transpose([[string(ABS(parsetimecheck-shift(parsetimecheck,1)), format="(F0.5)")],[parsetimelabels]])
  oData->SetAttribute, 'Note', 'Variables Parsed by IDL at '+SYSTIME()+' in '+STRCOMPRESS(STRING(SYSTIME(1)-StartParseTime),/REMOVE_ALL)+' s.'
  oDocument->Save, String=xmlstring, /PRETTY_PRINT
  
  if (where(mainlevelvars eq 'XTSM') ne -1) then (SCOPE_VARFETCH('XTSM', LEVEL=1, /ENTER)) = [SCOPE_VARFETCH('XTSM', LEVEL=1),xmlstring] else begin
    (SCOPE_VARFETCH('XTSM', LEVEL=1, /ENTER)) = xmlstring
  endelse
  
  OBJ_DESTROY, oDocument 
  
end



function XTSM_Package, data_payload
  ; this routine 'packages' the data payload returned by labview after a sequence is run
  ; it does this first by splitting the data up into blocks corresponding to each requested data item
  ; these blocks are then saved according to two possible methods:
  ; direct append - the data is directly appended to the XTSM node that generated the data
  ; heap and append reference -
  ; data is thrown on heap in main scope, and a reference to this data is appended to the XTSM node it originated from 
  ; the routine is incomplete as of 12/6/12 NDG
  
  ; Algorithm timing data
  StartPackageTime=SYSTIME(1)
  packagetimecheck=[SYSTIME(1)]
  packagetimelabels=['total package time']
  ; grab last xtsm string element from global context
  xtsmstring=(SCOPE_VARFETCH('XTSM', LEVEL=1, /ENTER))[-1]
  ; parse it into an object
  oDocument=open_xml_from_string(xtsmstring)
  
  stop
  ; add packager notes
  packagerNote=(oDocument->GetFirstChild())->AppendChild(oDocument->createElement('PackagerNote'))
  pnotetext=packagerNote->AppendChild(oDocument->createTextNode( 'Data References packaged by IDL at '+SYSTIME()+' in '+STRCOMPRESS(STRING(SYSTIME(1)-StartPackageTime, FORMAT="(F0.4)"),/REMOVE_ALL)+' s.'))
  oDocument->Save, String=xmlstring, /PRETTY_PRINT
  ; rewrite the last element of the xtsm stack
  ;(SCOPE_VARFETCH('XTSM', LEVEL=1, /ENTER))[0:-2]
end

function getChannelbyIndex,  channelMap ,timinggroupindex, timinggroup
; looks up a channel in the channelMap by group and index
  channels=channelMap->GetElementsByTagName('Channel')
  for j=0, (channels->getLength()-1) do $
    if ((((((channels->item(j))->GetElementsByTagName('TimingGroup'))->item(0))->GetFirstChild())->GetNodeValue() eq timinggroup )and(((((channels->item(j))->GetElementsByTagName('TimingGroupIndex'))->item(0))->GetFirstChild())->GetNodeValue() eq timinggroupindex )) then break
  return, channels->item(j)
end

function getNodeValue_orDefault, object, nodename, default
; fetches value of a child noe with node name nodename, if it exists and has a nontrivial value, else returns default value
  if (object eq !Null) then return, default
  if ((object->GetElementsByTagName(nodename))->GetLength() eq 0) then return, default 
  if ((((object->GetElementsByTagName(nodename))->item(0))->GetFirstChild()) ne !null) then val=(((object->GetElementsByTagName(nodename))->item(0))->GetFirstChild())->GetNodeValue() else return, default
  if (strcompress(val) ne '') then return, val else return, default 

end

function expand_sparse_control_array_from_file
; this expands a sparse (val,repeat) array into a full control array
; it is written in 'c-style' as a precursor to writing the pxi-ready routine
    ;OPENR, 1,  "c:\wamp\www\sequences\temp\TimingControlArray.dats"
    
    ; get header info for file
    numchan=bytarr(1,/nozero)
    readu, 1, numchan
    bytesperval=bytarr(1,/nozero)
    readu, 1, bytesperval
    bytesperrepeat=bytarr(1,/nozero)
    readu, 1, bytesperrepeat
    numtimes=bytarr(4,/nozero)
    readu, 1, numtimes
    byte4conv=((long(256))^indgen(long(4)))
    numtimes=total(numtimes*byte4conv,/integer)
    
    ca=uintarr(numchan,numtimes,/nozero)
    
    inval=bytarr(bytesperval,/nozero)
    valbyt=((long(256))^indgen(long(bytesperval)))
    inrep=bytarr(bytesperrepeat,/nozero)
    repbyt=((long(256))^indgen(long(bytesperrepeat)))

    for chan=0, (numchan[0]-1) do begin
      numbytesthischannel=bytarr(4,/nozero)
      readu, 1, numbytesthischannel
      numbytesthischannel=total(numbytesthischannel*byte4conv,/integer)
      length=numbytesthischannel/(bytesperrepeat+bytesperval)
      point=0
      for entry=0, length[0]-1 do begin
        readu, 1, inval & invali=total(inval*valbyt,/integer)
        readu, 1, inrep & inrepi=total(inrep*repbyt,/integer)
        ;if (entry ge 3000) then stop
        for j=point, point+inrepi-1 do ca[chan,j]=invali
        point=j
      endfor
    endfor
    CLOSE,1


return, ca

end

function expand_timingstring, ts
; this expands a sparse (val,repeat) array "ts" into a full control array
; it is written in 'c-style' as a precursor to writing the pxi-ready routine

    byte4conv=((long(256))^indgen(long(4)))    
    byte8conv=((long64(256))^indgen(long64(8)))    
    tslength=total(ts[0:7]*byte8conv,/integer)
    if (tslength ne n_elements(ts)) then return, "error on length"
    ; get header info for file
    numchan=ts[8]
    bytesperval=ts[9]
    bytesperrepeat=ts[10]
    numtimes=ts[11:14]
    numtimes=total(numtimes*byte4conv,/integer)
    
    ca=uintarr(numtimes,numchan,/nozero)
    
    inval=bytarr(bytesperval,/nozero)
    valbyt=((long(256))^indgen(long(bytesperval)))
    inrep=bytarr(bytesperrepeat,/nozero)
    repbyt=((long(256))^indgen(long(bytesperrepeat)))

    ptr=15

    for i=0, (numchan-1) do begin
      ptw=0
      numbytesthischannel=total(ts[ptr:ptr+3]*byte4conv,/integer)
      ptr+=4
      finind=numbytesthischannel+ptr-1
      ;if ((bytesperval eq 4) and (bytesperrepeat eq 4)) then begin
        while (ptr le finind) do begin
          inval=total(ts[ptr:ptr+bytesperval-1]*valbyt,/integer)
          ptr+=bytesperval
          inrep=total(ts[ptr:ptr+bytesperrepeat-1]*repbyt,/integer)
          ptr+=bytesperrepeat
          jlim=i*numtimes+ptw+inrep
          for j=i*numtimes+ptw, i*numtimes+ptw+inrep-1 do ca[j]=inval
          ptw+=inrep
        endwhile
      ;endif
    endfor
return, (ca)

end

pro expand_all_active_timingstrings

  mainlevelvars=scope_varname(level=1)
  timingstrings=strsplit(mainlevelvars[where(strpos(mainlevelvars,'ACTIVE_TIMINGSTRING_') ne -1)],'ACTIVE_TIMINGSTRING_',/regex,/extract)
  foreach timingstring, timingstrings do begin
    ts=SCOPE_VARFETCH('ACTIVE_TIMINGSTRING_'+timingstring,LEVEL=1)
    td=SCOPE_VARFETCH('ACTIVE_TIMINGDATA_'+timingstring,LEVEL=1)
    if (td[8] eq 1) then begin
      dca=expand_timingstring(ts)
      (SCOPE_VARFETCH('ACTIVE_DCA_'+timingstring,LEVEL=1,/ENTER))=dca
    endif else begin
      ;this performs byte-array to integer conversions
      ;note: bytespervalue=ts[9]
      ;note: bytespervalue=ts[10]
      b=ulong64(reform(ts[19:*],ts[9]+ts[10],(n_elements(ts)-19)/(ts[9]+ts[10])))
      for j=0, ts[9]-1 do b[j,*]=ishft(ulong64(b[j,*]),8*j)
      for j=0, ts[10]-1 do b[ts[9]+j,*]=ishft(ulong64(b[ts[9]+j,*]),8*j)
      if ((ts[9] ne 0)and(ts[10] eq 0)) then dca=total(b[0:ts[9]-1,*],1,/INTEGER)
      if ((ts[10] ne 0)and(ts[9] eq 0)) then dca=total(b[ts[9]:ts[10]-1,*],1,/INTEGER)
      (SCOPE_VARFETCH('ACTIVE_DCA_'+timingstring,LEVEL=1,/ENTER)) = dca
      
    endelse
  endforeach
end

function active_emulation
  expand_all_active_timingstrings
; this routine is UNFINISHED, but intended to build an emulation of the hardware output based on the timingstrings generator by the parser.
  em=SCOPE_VARFETCH('ACTIVE_EMULATIONMATRIX',LEVEL=1)
  ;sort the emulation matrix by clock chain order
  em=em[*,reverse(sort(em[1,*]))]
  
  foreach tg, em[0,*] do begin
    dca=SCOPE_VARFETCH('ACTIVE_DCA_'+string(tg, format="(I03)"),LEVEL=1)
    ;td=(SCOPE_VARFETCH('ACTIVE_timingdata_'+string(tg, format="(I03)"),LEVEL=1))[0:19]
    clockgroup=em[2,where(em[0,*] eq tg)]
    clockchannel=em[3,where(em[0,*] eq tg)]
    if (clockgroup ne -1) then clock_dcat=SCOPE_VARFETCH('ACTIVE_DCAt_'+string(clockgroup, format="(I03)"),LEVEL=1)
    if (em[5,where(em[0,*] eq tg)] eq 1) then begin
      ; this handles delaytrain emulation - creates a pulse one clock-cycle wide after each delay
      ;em_ctv is a matrix of channel (row index)x time (column index) of values.  The last row holds the universal time in ms at each time index.  
      em_ctv=[[reform(transpose([[make_array(n_elements(dca),value=1)],[make_array(n_elements(dca),value=0)]]),2*n_elements(dca))],[(em[6,(where(reform(em[0,*]) eq float(tg)))])[0]*total(reform(transpose([[dca],[make_array(n_elements(dca),value=1)]]),2*n_elements(dca)),/cumulative)]]
      (SCOPE_VARFETCH('ACTIVE_DCAt_'+string(tg, format="(I03)"),LEVEL=1,/ENTER))=em_ctv
      ;tplot holds an array of point-pairs to draw a timing plot.
      
    endif else begin
      
      ; this handles non-delaytrain groups
      ;identify rise-times on clocking channel from its dense control array (gauranteed to already have had its times appended by running this in clocking-order 
      
      risetimes=clock_dcat[where(clock_dcat[*,clockchannel] gt shift(clock_dcat[*,clockchannel],1)),-1]
      ;if (clock_dcat[-1,clockchannel] gt clock_dcat[-2,clockchannel] ) then risetimes=[risetimes,clock_dcat[-1,-1]]
      ;error - trap : if number of ristimes doesn't match number of elements, we are missing sample clock edges
      if (n_elements(risetimes) ne (size(dca))[1]) then begin
        print, "timing group "+string(tg, format="(I01)")+" has incorrect number of sample clock edges issued by group "+string(clockgroup, format="(I01)")+" channel "+string(clockchannel, format="(I01)")
        print, "--emulating hardware as it would behave"
        
        if (n_elements(risetimes) gt (size(dca))[1]) then risetimes=risetimes[0:((size(dca))[1]-1)]
        if (n_elements(risetimes) lt (size(dca))[1]) then risetimes=[risetimes,10000.0D*dindgen((size(dca))[1]-n_elements(risetimes))]
      endif
      
      ;if this group is a digital group represented by a n-byte integer, expand it into an array of booleans, with extra (last) row update times, otherwise just add update times
      if ((size(dca))[0] eq 1) then em_ctv=rotate([[transpose(risetimes)],(integerarray_to_2Dbits(reform(dca[*,0]),em[7,where(em[0,*] eq tg)]))],3) else em_ctv=[[dca],[risetimes]]
      
      
      (SCOPE_VARFETCH('ACTIVE_DCAt_'+string(tg, format="(I03)"),LEVEL=1,/ENTER))=em_ctv
      
    endelse
  endforeach
  return, 1
end

pro plot_timeseries, em_ctv, channel
     tplot =[[(reform(transpose(reform([[reform(em_ctv[*,channel])],[reform(em_ctv[*,channel])]])),2*n_elements(em_ctv[*,channel])))[0:-2]],[(shift(reform(transpose(reform([[reform(em_ctv[*,-1])],[reform(em_ctv[*,-1])]])),2*n_elements(em_ctv[*,-1])),-1))[0:-2]]]
     plot, tplot[*,1], (tplot[*,0]/max(tplot[*,0])) , yrange=[-1,2]  
end
pro plot_timeseriess, em_ctv, CHANNELS=channels, VGRID=vgrid
     if (not keyword_set(CHANNELS)) then channels=INDGEN((size(em_ctv))[2]-1)
     pxmin=min(em_ctv[*,-1])-.01*(max(em_ctv[*,-1])-min(em_ctv[*,-1]))
     pxmax=max(em_ctv[*,-1])+.01*(max(em_ctv[*,-1])-min(em_ctv[*,-1]))
     pymin=-1
     pymax=3+3*n_elements(channels)
     plot,[0],[0],yrange=[pymin,pymax], xrange=[pxmin,pxmax]
     times=em_ctv[*,-1]
     if (keyword_set(vgrid)) then foreach time, times do oplot, [time,time],[pymin,pymax], color='555555'x
     offset=-3
     channum=-1
     foreach channel, channels do begin
      offset+=3
      channum++
      tplot =[[(reform(transpose(reform([[reform(em_ctv[*,channel])],[reform(em_ctv[*,channel])]])),2*n_elements(em_ctv[*,channel])))[0:-2]],[(shift(reform(transpose(reform([[reform(em_ctv[*,-1])],[reform(em_ctv[*,-1])]])),2*n_elements(em_ctv[*,-1])),-1))[0:-2]]]
      oplot, [pxmin,pxmax], [offset,offset], linestyle=1, color='555555'x
      oplot, [pxmin,pxmax], [offset+1,offset+1], linestyle=1, color='5555ff'x
      oplot, tplot[*,1], offset+((tplot[*,0]-min([tplot[*,0],1]))/(max([tplot[*,0],1])-min([tplot[*,0],1])))
      xyouts, pxmin-.05*(pxmax-pxmin),offset-1. ,"gX:"+string(channum, format="(I02)")
     endforeach  
end
pro plot_active_timeseriesss, CHANNELS=channels, VGRID=vgrid, xrange=XRANGE
     ; find all dense control arrays
     mainlevelvars=scope_varname(level=1)
     dcats=strsplit(mainlevelvars[where(strpos(mainlevelvars,'ACTIVE_DCAT_') ne -1)],'ACTIVE_DCAT_',/regex,/extract)
     dcatn=!null
     foreach dcat,dcats do dcatn=[dcatn,fix(dcat)]
     ; if desired channels are not defined, get all channels as group, index pairs
     if (not keyword_set(CHANNELS)) then begin
       channels=!null
       foreach dcat,dcatn do begin
          em_ctv=SCOPE_VARFETCH('ACTIVE_DCAT_'+string(dcat, format="(I03)"),LEVEL=1)
          channels=[[channels],([[make_array((size(em_ctv))[2]-1,value=dcat)],[INDGEN((size(em_ctv))[2]-1)]])]
       endforeach
       channels=transpose(channels)
     endif
     ; determine bounds of graph
     pxmin=0 & pxmax=0
     pymin=-1
     pymax=3+3*(size(channels))[2]
     times=!null
     foreach dcat,dcatn do begin
       em_ctv=SCOPE_VARFETCH('ACTIVE_DCAT_'+string(dcat, format="(I03)"),LEVEL=1)
       pxmin=min([min(em_ctv[*,-1])-.01*(max(em_ctv[*,-1])-min(em_ctv[*,-1])),pxmin])
       pxmax=max([max(em_ctv[*,-1])+.01*(max(em_ctv[*,-1])-min(em_ctv[*,-1])),pxmax])
       times=[times,em_ctv[*,-1]]
     endforeach
     if (keyword_set(xrange)) then begin & pxmin=xrange[0] & pxmax=xrange[1] & endif
     plot,[0],[0],yrange=[pymin,pymax], xrange=[pxmin,pxmax]
     if (keyword_set(vgrid)) then foreach time, times do oplot, [time,time],[pymin,pymax], color='555555'x
     
     offset=-3
     channum=-1
     for channum=0,(size(channels))[2]-1 do begin
      offset+=3
      em_ctv=SCOPE_VARFETCH('ACTIVE_DCAT_'+string(channels[0,channum], format="(I03)"),LEVEL=1)
      tplot =[[(reform(transpose(reform([[reform(em_ctv[*,channels[1,channum]])],[reform(em_ctv[*,channels[1,channum]])]])),2*n_elements(em_ctv[*,channels[1,channum]])))[0:-2]],[(shift(reform(transpose(reform([[reform(em_ctv[*,-1])],[reform(em_ctv[*,-1])]])),2*n_elements(em_ctv[*,-1])),-1))[0:-2]]]
      oplot, [pxmin,pxmax], [offset,offset], linestyle=1, color='555555'x
      oplot, [pxmin,pxmax], [offset+1,offset+1], linestyle=1, color='5555ff'x
      oplot, tplot[*,1], offset+((tplot[*,0]-min([tplot[*,0],1]))/(max([tplot[*,0],1])-min([tplot[*,0],1])))
      xyouts, pxmin-.05*(pxmax-pxmin),offset ,"g"+string(channels[0,channum], format="(I01)")+":"+string(channels[1,channum], format="(I02)")
     endfor
end

function integerarray_to_2Dbits, in, numbits
; function to convert 1D array of integers into 2D array (mostly for visual inspection of free-clocked control array)
    s=size(in)
    b=Reform(binary(long(in)),32,s[1])
    if keyword_set(numbits) then return, b[-numbits:*,*] else return, b
end

function errorflag, message
print, message
return, message
end

function binary, number
;+
; Name:
;   binary
; Purpose:
;   Returns the binary representation of a number of any numerical type.
; Argument:
;   number    scalar or array of numbers (any numerical type)
; Returns:
;   Byte array with binary representation of numbers.
; Examples:
;   Binary representation of 11b:
;     IDL> print, binary(11b)
;     0 0 0 0 1 0 1 1
;   Binary representation of pi (x86: Little-endian IEEE representation):
;     IDL> print, format='(z9.8,5x,4(1x,8i1))', long(!pi,0), binary(!pi)
;      40490fdb      01000000 01001001 00001111 11011011 (x86 Linux)
;      0fdb4149      00001111 11011011 01000001 01001001 (Alpha OpenVMS)
;     IDL> print, format='(8(1x,8i0))', binary(!dpi)
;      01000000 00001001 00100001 11111011 01010100 01000100 00101101 00011000
;   Some first tests before type double was added:
;     print, format='(2a6,4x,2z9.8,4x,8z3.2)', $
;       !version.arch, !version.os, long(!dpi,0,2), byte(!dpi,0,8)
;       x86 linux     54442d18 400921fb     18 2d 44 54 fb 21 09 40
;     sparc sunos     400921fb 54442d18     40 09 21 fb 54 44 2d 18
;     alpha   vms     0fda4149 68c0a221     49 41 da 0f 21 a2 c0 68
;     (Beginning with IDL 5.1, Alpha VMS uses IEEE representation as well.)
; Modification history:
;    19 Dec 1997  Originally a news posting by David Fanning.
;                       (Re: bits from bytes)
;    20 Dec 1997  "Complete" rewrite: eliminate loops.
;    22 Dec 1997  Bit shift instead of exponentiation, return byte
;     array, handle input arrays.
;     Think about double and complex types.
;    22 Sep 1998  Complete rewrite: reduce every numerical type to
;     single bytes. Check that big and little endian machines
;     return exactly the same results (if IEEE).
;-
  s = size(number)
  type = s[s[0] + 1]
  n_no = s[s[0] + 2]
; Numerical types: (will have to be completed if IDL adds double-long, ...)
; 1: byte             (1-byte unsigned integer)
; 2: integer          (2-byte   signed integer)
; 3: long             (4-byte   signed integer)
; 4: floating-point   (4-byte, single precision)
; 5: double-precision (8-byte, double precision)
; 6: complex        (2x4-byte, single precision)
; 9: double-complex (2x8-byte, double precision)
; Non-numerical types:
; 0: undefined, 7: string, 8: structure, 10: pointer, 11: object reference
  nbyt = [0, 1, 2, 4, 4, 8, 8, 0, 0, 16, 0, 0] ; number of bytes per type
  ntyp = nbyt[type]
  if ntyp eq 0 then message, 'Invalid argument (must be numerical type).'
  bits = [128, 64, 32, 16,  8,  4,  2,  1] ; = ishft(1b, 7-indgen(8))
; For correct array handling and byte comparison, 'number' and 'bits' require
; same dimensions -> numvalue and bitvalue
  bitvalue = ((bits)[*, intarr(ntyp)])[*, *, intarr(n_no)]
  little_endian = (byte(1, 0, 1))[0]
; In case of complex type and little endian machine, swap the two float values
; before the complete second dimension is reversed at returning.
  if (type eq 6 or type eq 9) and little_endian then $ ; type complex
    numvalue = reform((byte([number], 0, 1, ntyp/2, 2, n_no))$
                      [intarr(8), *, [1,0], *], 8, ntyp, n_no) $
  else numvalue = (byte([number], 0, 1, ntyp, n_no))[intarr(8), *, *]
; On little endian machines, the second dimension of the return value must
; be reversed.
  if little_endian then $
    return, reverse((numvalue and bitvalue) ne 0, 2) else $
    return,         (numvalue and bitvalue) ne 0
end