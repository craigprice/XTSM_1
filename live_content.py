# -*- coding: utf-8 -*-
"""
Created on Mon Apr 21 17:01:33 2014

@author: Nate
"""
import uuid,time, operator, warnings, pdb, random
import XTSM_Server_Objects

LIVE_CONTENT_MANAGER_MAXDATA=100000000  # total memory in bytes allowed in single manager's content storage 
LIVE_CONTENT_MANAGER_MAXFRAC=15  # percentage of total data a single element's content may occupy

class Live_Content(XTSM_Server_Objects.XTSM_Server_Object,object):
    """
    inheritance class for live content objects, which provide server-side storage, delivery
    and manipulation of GUI items such as figures - 
    
    it is assumed some objects inheriting this class will also inherit the XTSM_core class;
    several of its methods (particularly, e.g. onchange event firing) over-ride this
    base class
    
    a simple example subclass of Live_Content, live_icon, is written into the definition
    of Live_Content_Manager
    """
    class MethodUndefinedError(Exception):
        pass
    def _generate_live_content(self):
        """
        this method should be overridden by inheriters to provide live
        content to requestors
        """
        raise self.MethodUndefinedError

    def _user_callback(self,params):
        """
        this is a default user interaction even callback routine for live content
        it will be called from the GUI through the server whenever a user invokes
        a live_content_event(this,args...) call in javascript GUI - the args will be
        returned in params, along with content_id, etc...         
        
        this method can be overridden by inheriters to provide interactive
        responses to users - it will be provided to the live content manager,
        which will call it on user activity
        """
        try: getattr(self,params['args'][0])(params['args'][1:])        
        except Exception as e: 
            print e
            raise self.MethodUndefinedError
        
    def __generate_id__(self):
        self.content_id=uuid.uuid1()

    def __init__(self,params={}):
        self.time_created=time.time()
        self.__generate_id__()        
        defaultparams={"expire_at":self.time_created+3600.,"expire_after":500.}
        defaultparams.update(params)
        for item in defaultparams: setattr(self,item,defaultparams[item])
        
    elements_to_fire_onChange=[]  # override this with a list of attributes that if changed should change the live_content
    
    def __setattr__(self,att,val):
        """
        this method overrides attribute set mechanisms to additionally fire the
        self.onChange method if the attribute is whitelisted for content update
        """
        object.__setattr__(self,att,val)
        if att in self.elements_to_fire_onChange:
            self.onChange(getattr(self,att))

    def onChange(self,elm=None):
        """
        default onchange element - any objects tagged (using registerListener) 
        as needing notifications of a change on this element
        will have their callback method called
        
        note that the XTSM core class overrides this method.
        """
        try: 
            for listener in self._registeredListeners:  
                params = self._registeredListeners[listener]
                params.update({"changed_element":self})
                self._registeredListeners[listener]['method'](params)  # calls the callback associated in the dictionary
        except AttributeError: pass

    def registerListener(self,listener_callback):
        """
        registers a callback mechanism to call when this item has changed
        
        this is overwritten in the XTSM classes by the core class inheritance
        but for non-XTSM objects inheriting this class, this is the base method
        """
        if type(listener_callback)!=type({}): 
            listener_callback={"method":listener_callback}        
        listener_callback.update({"listener_id":str(uuid.uuid1())})
        if not hasattr(self,"_registeredListeners"): self._registeredListeners={}
        self._registeredListeners.update({listener_callback['listener_id']:listener_callback})
        return listener_callback['listener_id']

    def deregisterListener(self,listener_id):
        """
        removes a listener from service
        """
        try: del self._registeredListeners[listener_id]
        except AttributeError: return False
        except KeyError: return False
        return True

class Live_Content_Manager(XTSM_Server_Objects.XTSM_Server_Object, dict):
    """
    manager class for server live content - holds a dictionary of 
    live content items (values) and their content_id tags (keys)
    """
    def __init__(self):
        self.max_data=LIVE_CONTENT_MANAGER_MAXDATA
        self.provided_to={}
        self.inserted_at={}
        self.content={}
        self.last_generation_cost={}
        self.last_generation_time={}
        self.listenerIDs={}
        self.last_change={}
        
    def flush(self):
        """
        checks for dead elements and performs cleanup, if the stack is over
        maximum size, will eject the content of the least computationally 
        valuable elements (utilization interval / computation time) until size is below this limit
        """
        now=time.time()
        retentionvalue={}
        sz=self.size()
        for item in self:
            if self[item]['expire_at'] < now: 
                del self[item]
                continue
            if (now-max(self.provided_to[item].values()))>self[item]['expire_after']: 
                del self[item]
                continue
            if sz>self.max_data: 
                retentionvalue.update({item:(self.last_generation_cost/(now-max(self.provided_to[item].values())))})
        if sz>self.max_data: 
            droplist=sorted(retentionvalue.iteritems(), key=operator.itemgetter(1)).reverse()
            while self.size()>self.max_data:
                self.content[droplist.pop()[0]]=None                        
            
    def get_content(self, content_id,requester='unknown'):
        """
        returns current content of an item by content_id -
        this is taken from local content storage if it exists, or is requested from
        live data element if not.  logs timestamp
        and record of requestor (optional identifier - can be any data type, but
        preference is a websocket protocol); also keeps track of time taken to generate content
        """
        #pdb.set_trace()
        if (content_id=="1234" and not self.has_key("1234")):   # for testing purposes - can be removed
            self.update({"1234":self.live_icon(requester)})
        if self.has_key(content_id): 
            if self.content[content_id]!=None:
                c=self.content[content_id]
            else: 
                then=time.time()
                c=self[content_id]._generate_live_content()
                self.last_generation_cost.update({content_id:(time.time()-then)})
                self.last_generation_time.update({content_id:time.time()})
        else: return ""
        self.content.update({content_id:c})
        self.provided_to[content_id].update({requester:time.time()})
        return c
        
    class ContentUnknownError(Exception):
        pass
    class CannotManageThisError(Exception):
        pass
            
    def size(self):
        """
        returns size, in bytes, of the live content storage
        """
        return sum([len(s) for s in self.content.values])
    
    def __setitem__(self,item,val):
        """
        inserts a live content item into manager; a listener is registered to
        the item to callback and notify the manager when content has changed
        """
        if (not isinstance(val,Live_Content)): raise self.CannotManageThisError
        dict.__setitem__(self,item,val)
        self.provided_to.update({item:{}})
        self.inserted_at.update({item:time.time()})
        self.content.update({item:None})
        self.last_change.update({item:None})
        try: 
            self.listenerIDs.update({item:val.registerListener({'method':self._item_changed, 'content_id':item})})
        except AttributeError: 
            self.listenerIDs.update({item:None})

    def update(self,dictin):
        """
        standard dictionary update method; (calls __setitem__)
        """
        for item in dictin:
            self.__setitem__(item,dictin[item])
            
    def registerEvent(self,params):
        """
        registers a server-necessary event back from a live data item in the GUI - 
        calls the live data element's corresponding method
        """
        try: self[params['content_id']]._user_callback(params)
        except: pass
            
    def _item_changed(self,params):
        """
        fired when a live_data item is changed (installed as a callback to listener on the item)
        resets the local content storage to None*, and notifies consumers of change
        
        * possible improvement: if last_generation_cost exceeds is high, and the
        consumers are known to request data on change, the manager
        could immediately request new data for local storage rather than wait for a new request
        from consumer
        """
        self.content[params['content_id']]=None
        self.last_change.update({params['content_id']:time.time()})
        for user in self.provided_to[params['content_id']]:
            try: self._find_message_method(user)('{"live_content_changed":{"content_id":"'+params['content_id']+'"}}')
            except AttributeError: warnings.warn("live content provided to object without a sendMessage method - cannot notify of element changes") 
        
    def _find_message_method(self,comm_identifier):
        """
        finds a write method inside a communication identifier
        """
        for elm in ["request","protocol","write",""]:
            if hasattr(comm_identifier,'sendMessage'): return comm_identifier.sendMessage
            if comm_identifier.has_key(elm): comm_identifier=comm_identifier[elm]
        raise AttributeError
        return
        
    class live_icon(Live_Content):
        """
        example / tester class for checking onchange elements, etc - demonstrates
        onChange refreshes to GUI (automatically cycle through set of images on server delay),
        and two types of user interaction ; stops/starts on a click using server callback; grows on
        mouseover using browser method.  
        
        in new classes of objects, simple operations should be done in browser to
        minimize redraws and server burden
        """
        elements_to_fire_onChange = ["ind"]        
        
        def __init__(self,requester):            
            Live_Content.__init__(self)
            self.iterate=True
            self.ind=0
            self.l=requester.factory.parent.task.LoopingCall(self.cycle)
            self.icon_stack=["seqicon_item_addGraph.png","seqicon_item_addTimingGroupData.png","seqicon_default.png","seqicon_building.svg"]
            self.l.start(2, now=False)            
            
        def cycle(self):
            if self.iterate: self.ind+=1
            
        def _generate_live_content(self):
            return "<img src=../images/" + self.icon_stack[self.ind%4]+" height='25px' onclick='live_content_event(this,\"on_aclick\");' onmouseover='this.setAttribute(\"height\",\"50px\");' onmouseout='this.setAttribute(\"height\",\"25px\");' />"
        
        def on_aclick(self,params):
            self.iterate = not self.iterate 