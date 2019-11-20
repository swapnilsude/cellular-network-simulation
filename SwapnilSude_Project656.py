import numpy as np
import matplotlib.pyplot as plt
import time

"""Python application which will simulate the downlink behavior of two basestations
covering a stretch of road between them.
This script takes distance between two basestations, simulation time, # of users,
user speed as input and provides hourly reports of simulation as well as final summary 
after complete simulation.
"""

###################### Basic Parameters ######################
BS_POSITION=int(input("Enter distance between two basestations in Km: "))#12 #kilometers  
S_TIME_STEP_SIZE=1 #sec
T_SIM_TIME=int(input("Enter simulation time in hours: "))#4 #hours   
###################### Basestation Parameters ######################
BS_HEIGHT=50 #meters
EIRP=55 #dBm
NO_TCH=30 #30 TRAFFIC CHANNELS
FREQ=1000 #MHz
###################### User Parameters ######################
UE_HEIGHT=1.7 #meters
RSL=-102 #dBm
NO_OF_USERS=int(input("Enter total users on road: "))#1000 
CALL_RATE=1   #lambda  call per hour
CALL_RATE_CON=CALL_RATE/3600   #call rate lambda per second
AVG_CALL_DUR=3 # H 3 minutes per call
UE_SPEED=int(input("Enter speed in m/s: "))#15 # meters per sec 
HO_TIMER=3
SHAD_RES=10 #meters

#to calculate execution time of simulation
start = time.time()

#np.random.seed(2020) #seeding the numpy random generator

###################### Initializing variables ######################

#variables to count blocked calls 
call_blocked_pwr1=call_blocked_pwr2=call_blocked_cap1=call_blocked_cap2=0
call_success_1=call_success_2=0
#variables to count dropped calls
call_dropped_bs1=call_dropped_bs2=0
#variables to count attempted and the calls that connect
call_attempted=call_attempted1=call_attempted2=0
call_connected1=call_connected2=0
call_started=0
#no of calls handovered by each cell and related parameters
hand12attempt=hand21attempt=hand12success=hand21success=hand12fail_cap=hand21fail_cap=0
hand12drop=hand21drop=0

#index and call duration of users that are on call ar BS1
#tch1_index and tch1_call_duration is like an table consisting of users connected ot BS1 and their duration
tch1_index=np.array([],dtype=int)
tch1_call_duration=np.array([],dtype=int)
#index and call duration of users that are on call ar BS2
#tch2_index and tch2_call_duration is like an table consisting of users connected ot BS2 and their duration
tch2_index=np.array([],dtype=int)
tch2_call_duration=np.array([],dtype=int)
#Current handover calls. handoverXcall=>handover timer, 
#handoverXcall_index=>index of users on handover, handoverXcall_duration=>call duration of user on handover
#handoverXcall, handoverXcall_index and handoverXcall_duration is like an table consisting of 
#handover time, users in handover and their duration
handover1call=np.array([],dtype=int)
handover2call=np.array([],dtype=int)
handover1call_index=np.array([],dtype=int)
handover1call_duration=np.array([],dtype=int)
handover2call_index=np.array([],dtype=int)
handover2call_duration=np.array([],dtype=int)

###################### Functions  ######################

#function to calculate propogation loss
def propagation_loss(d):
    ahm=(1.1*np.log10(FREQ)-0.7)*UE_HEIGHT-(1.56*np.log10(FREQ)-0.8)
    OH=69.55+26.16*np.log10(FREQ)-13.82*np.log10(BS_HEIGHT)+(44.9-6.55*np.log10(BS_HEIGHT))*np.log10(d/1000)-ahm
    return OH

#function to calculate shadowing
def shadowing():
    #mean=0, std_div=2, size=BS_POSITION*100
    #shadow1 is for bs1 
    shadow1=np.random.normal(0, 2, size=BS_POSITION*int(1000/SHAD_RES))
    #shadow2 is for bs2. Note: Here 1st value is for the furthest shadow
    shadow2=np.random.normal(0, 2, size=BS_POSITION*int(1000/SHAD_RES))#int((BS_POSITION*100)/SHAD_RES)
    return shadow1,shadow2

#function to calculte fading
# Note : d isn't used inside the function. It is just used for vectorizing the RSL calculation
# i.e. to make function callable each time RSL is calculated
def fading(d=None):
#    zero mean and unit varience(therefore, std_div=1)
    x = np.random.normal(0,1,10)
    y = np.random.normal(0,1,10)
    z=x+y*(1j)
    ray_dis=np.abs(z)
#    ray_dis=np.random.rayleigh(1,10)
    ray_dis = np.sort(ray_dis)
    #taking the second deepest fade
    return (20*np.log10(ray_dis[1]))
#    x = np.random.normal(0,1,10)
#    x=np.sort(x)
#    y = np.random.normal(0,1,10)
#    y=np.sort(y)
#    z=x[1]+y[1]*(1j)
#    ray_dis=np.abs(z)
#    return 20*np.log10(ray_dis)

#vectorizing fading function
vfading=np.vectorize(fading,otypes=[float])

#function to calculte rsl for distance d
def rsl_cal(d):
    #calls function propogation loss and fading
    #d/10 provides shadow value for that distance
    rsl_bs1=EIRP-(propagation_loss(d))+shadow1[int(d/10)]+fading()
    rsl_bs2=EIRP-(propagation_loss(BS_POSITION*1000-d))+shadow2[int(d/10)]+fading()
    return rsl_bs1,rsl_bs2

#function to calculate RSL 
def rsl_cal_vec(d):
    rsl_bs1=EIRP-(propagation_loss(d))+shadow1[(d/10).astype(int)]+vfading(d)
    rsl_bs2=EIRP-(propagation_loss(BS_POSITION*1000-d))+shadow2[(d/10).astype(int)]+vfading(d)
    return rsl_bs1,rsl_bs2

def call_duration(): 
    #scale => avg call duration # *60 for converting to sec
    return int(np.random.exponential(AVG_CALL_DUR*60))

#function to process the initialized calls
def check_call(possible_usr_call):
    global tch1_call_duration,tch1_index,tch2_index,tch2_call_duration
    global call_attempted,call_attempted1,call_attempted2,call_started,handover1call_index,handover2call_index
    global call_blocked_pwr1,call_blocked_pwr2,call_blocked_cap1,call_blocked_cap2,call_connected1,call_connected2
    
    call_attempted+=(len(possible_usr_call))
    #distances of the user who have initialized calls
    d=user_loc_array[possible_usr_call]
    #counter to be used for below for loop
    counter=0
    #for every distance (cnt) in d
    for cnt in d:
        #traffic channel used on BS1 is sum of lenghts of array tch1_index(which has index of users connected to BS1),
        #handover1call_index(call on handover from BS1 to BS2) and handover1call_index (call on handover from BS2 to BS1)
        #as calls in handover state occupy channels on both BS
        #simlarly for TCH used for BS2
        tch1_used=len(tch1_index)+len(handover2call_index)+len(handover1call_index)
        tch2_used=len(tch2_index)+len(handover2call_index)+len(handover1call_index)
        #calculate rsl1 and rsl2 for that distance
        rsl_bs1,rsl_bs2=rsl_cal(cnt)
        rsl_max=max(rsl_bs1,rsl_bs2)
        #if maximum RSL is from BS1 call is attempted to connect to BS1
        if rsl_max==rsl_bs1:
            call_attempted1+=1
        #if maximum RSL is from BS2 call is attempted to connect to BS2
        if rsl_max==rsl_bs2:
            call_attempted2+=1
        #if max RSL is greater than RSL threshold
        if rsl_max>=RSL:
            #when call is attempted to connect to BS1
            if rsl_max==rsl_bs1:
                #check if channels are available on BS1
                if tch1_used<NO_TCH:
                    #if yes append that index to tch1_index (which has index of users connected to BS1)
                    #also generating call durantion for that user.
                    tch1_index=np.append(tch1_index,possible_usr_call[counter])
                    tch1_call_duration=np.append(tch1_call_duration,call_duration())
                    call_connected1+=1 #call is connected to BS1
                else:
                    call_blocked_cap1+=1 #call is blocked due to capacity at BS1
                    #attempt to connected to BS2 if its RSL is greater than threshold and there are channels available
                    if ( rsl_bs2>=RSL and tch2_used<NO_TCH ):
                        tch2_index=np.append(tch2_index,possible_usr_call[counter])
                        tch2_call_duration=np.append(tch2_call_duration,call_duration())      
                        call_connected2+=1 #call connected to BS2
            #similar ot above if just for BS2
            elif rsl_max==rsl_bs2:
                if tch2_used<NO_TCH:
                    tch2_index=np.append(tch2_index,possible_usr_call[counter])
                    tch2_call_duration=np.append(tch2_call_duration,call_duration())
                    call_connected2+=1
                else:
                    call_blocked_cap2+=1
                    if ( rsl_bs1>=RSL and tch1_used<NO_TCH ):
                        tch1_index=np.append(tch1_index,possible_usr_call[counter])
                        tch1_call_duration=np.append(tch1_call_duration,call_duration())
                        call_connected1+=1
        #if max RSl is not greater than threshold call is blocked due to low power on respective BS
        else:
            if rsl_max==rsl_bs1:
                call_blocked_pwr1+=1
            if rsl_max==rsl_bs2:
                call_blocked_pwr2+=1
        counter+=1

#function to manage the users who are on call
def oncallusers():
    global tch1_call_duration,tch1_index,tch2_index,tch2_call_duration
    global handover1call,handover2call,call_dropped_bs1,call_dropped_bs2
    global handover1call_index,handover2call_index,handover1call_duration,handover2call_duration
    global call_success_1,call_success_2,call_blocked_cap1,call_blocked_cap2
    global hand12attempt,hand21attempt,hand12success,hand21success,hand12fail_cap,hand21fail_cap
    
    #reducing the call duration by step size here 1sec
    tch1_call_duration=tch1_call_duration-S_TIME_STEP_SIZE
    tch2_call_duration=tch2_call_duration-S_TIME_STEP_SIZE
    handover1call_duration=handover1call_duration-S_TIME_STEP_SIZE
    handover2call_duration=handover2call_duration-S_TIME_STEP_SIZE
    
    #removing terminated calls
    #finding the index of where call duration is 0 (call timer run out) or less and then removing that entry 
    #from the table (pair of tch1_index and tch1_call_duration) these calls are successful calls so increment
    #by the number of users whose call timer has run out
    #similarly for BS2 and calls on handover table as well
    index1=np.where(tch1_call_duration<=0)
    index2=np.where(tch2_call_duration<=0)
    index3=np.where(handover1call_duration<=0)
    index4=np.where(handover2call_duration<=0)
    
    call_success_1=call_success_1+len(index1[0])+len(index3[0])
    call_success_2=call_success_2+len(index2[0])+len(index4[0])
    
    tch1_call_duration=np.delete(tch1_call_duration,index1[0])
    tch1_index=np.delete(tch1_index,index1[0])
    
    tch2_call_duration=np.delete(tch2_call_duration,index2[0])
    tch2_index=np.delete(tch2_index,index2[0])
    
    handover1call=np.delete(handover1call,index3[0])
    handover1call_index=np.delete(handover1call_index,index3[0])
    handover1call_duration=np.delete(handover1call_duration,index3[0])
    handover2call=np.delete(handover2call,index4[0])
    handover2call_index=np.delete(handover2call_index,index4[0])
    handover2call_duration=np.delete(handover2call_duration,index4[0])    

    #removing below threshold 
    #vectorised calculation finding the RSL values for the uses connected to BS1 and BS2
    #d is array of users distances for its respective BS
    ### These RSL values calculated are now used along with the table of index and call duration ###
    ### So that we can use them latter for managing handoff  ###
    d1=user_loc_array[tch1_index]
    tch1rsl_1,tch1rsl_2=rsl_cal_vec(d1)
    d2=user_loc_array[tch2_index]
    tch2rsl_1,tch2rsl_2=rsl_cal_vec(d2)
    
    #index wehre RSL is less than threshold RSl
    temp1=np.where(tch1rsl_1<RSL)
    #if there are any such values
    if len(temp1[0])>0:
#        print(d1)
#        print(tch1rsl_1,"aaa")
#        print(tch1rsl_1[temp1],d1[temp1],call_dropped_bs1,temp1[0])
        #len of where RSL is less than threshold gives call drop for that duration
        call_dropped_bs1=call_dropped_bs1+len(temp1[0])
        #deleting these values from the table
        tch1_index=np.delete(tch1_index,temp1[0])
        tch1_call_duration=np.delete(tch1_call_duration,temp1[0])
        tch1rsl_1=np.delete(tch1rsl_1,temp1[0])
        tch1rsl_2=np.delete(tch1rsl_2,temp1[0])
    #similarly of bs2
    temp2=np.where(tch2rsl_2<RSL)
    if len(temp2[0])>0:
        #print(tch2rsl_2[temp2])
        call_dropped_bs2=call_dropped_bs2+len(temp2[0])#$$$$$$$$$$$$$
        tch2_index=np.delete(tch2_index,temp2[0])
        tch2_call_duration=np.delete(tch2_call_duration,temp2[0])
        tch2rsl_1=np.delete(tch2rsl_1,temp2[0])
        tch2rsl_2=np.delete(tch2rsl_2,temp2[0])
    
    # checking for handover
    # checking where is RSL from BS1 if less than RSL from BS2 for users on BS1
    tmp1=np.where(tch1rsl_1<tch1rsl_2)
    # this indicates handover attempted from BS1 to BS2
    hand12attempt=hand12attempt+len(tmp1[0])
    ind_hand=np.array([],dtype=int) #index of users on handover state
    # if there are any user for handoff
    if len(tmp1[0])>0:
        #for each user on handoff
        for counter1 in tmp1[0]:
            #channels used by BC2
            ontch2=len(tch2_index)+len(handover1call_index)+len(handover2call_index)
            # if there are channels available on BS2
            if (ontch2<NO_TCH):
                #add such users on handover table with Handover timer initialised to HO_TIMER
                #adding users from BS1 to handover state
                handover1call=np.append(handover1call,HO_TIMER)
                handover1call_duration=np.append(handover1call_duration,tch1_call_duration[counter1])
                handover1call_index=np.append(handover1call_index,tch1_index[counter1])
                ind_hand=np.append(ind_hand,counter1)
            else:
                #if there is no channel available on BS2 then counted as handover fail from BS1 to BS2
                #and also as call blocked due to capacity on BS2 
                hand12fail_cap+=1
#                call_blocked_cap2+=1
        #removing the handover calls from table of BS1 as these are now 
        #present in table of handover from BS1 to BS2
        tch1_index=np.delete(tch1_index,ind_hand)
        tch1_call_duration=np.delete(tch1_call_duration,ind_hand)
    
    #simlarly for calls handover from BS2 to BS1
    tmp2=np.where(tch2rsl_1>tch2rsl_2)
    hand21attempt=hand21attempt+len(tmp2[0])
    ind_hand2=np.array([],dtype=int)#index of handover in process
    if len(tmp2[0])>0:
        for counter2 in tmp2[0]:
            ontch1=len(tch1_index)+len(handover1call_index)+len(handover2call_index)
            if (ontch1<NO_TCH):
                handover2call=np.append(handover2call,HO_TIMER)
                handover2call_duration=np.append(handover2call_duration,tch2_call_duration[counter2])
                handover2call_index=np.append(handover2call_index,tch2_index[counter2])
                ind_hand2=np.append(ind_hand2,counter2)
            else:
                hand21fail_cap+=1
#                call_blocked_cap1+=1
        tch2_index=np.delete(tch2_index,ind_hand2)
        tch2_call_duration=np.delete(tch2_call_duration,ind_hand2)      
        
#function to manage user on handover state
def handover():
    global tch1_call_duration,tch1_index,tch2_index,tch2_call_duration
    global handover1call,handover2call,call_dropped_bs1,call_dropped_bs2
    global handover1call_index,handover2call_index,handover1call_duration,handover2call_duration
    global hand12success,hand21success,hand12drop,hand21drop
    
    #decreasing the handover timer for both handover tables
    handover1call=handover1call-S_TIME_STEP_SIZE
    handover2call=handover2call-S_TIME_STEP_SIZE
    #temp variables storing where handover time is 0 or less
    tmp3=np.where(handover1call<=0)
    tmp4=np.where(handover2call<=0)
    #for handover from BS1 to BS2 
    #when the handover timer is done transfer those calls to BS2 table and remove 
    #from handover table of BS1 to BS2
    tch2_index=np.append(tch2_index,handover1call_index[tmp3])
    tch2_call_duration=np.append(tch2_call_duration,handover1call_duration[tmp3])
    hand12success=hand12success+len(tmp3[0])
    handover1call=np.delete(handover1call,tmp3)
    handover1call_index=np.delete(handover1call_index,tmp3)
    handover1call_duration=np.delete(handover1call_duration,tmp3)
    #similarly for handover from BS2 to BS1
    tch1_index=np.append(tch1_index,handover2call_index[tmp4])
    tch1_call_duration=np.append(tch1_call_duration,handover2call_duration[tmp4])
    hand21success=hand21success+len(tmp4[0])
    handover2call=np.delete(handover2call,tmp4)
    handover2call_index=np.delete(handover2call_index,tmp4)
    handover2call_duration=np.delete(handover2call_duration,tmp4)
    
    #checking if calls in table of handover of BS1 to BS2 are getting below RSL threshold 
    #if yes removing those calls from table
    dis1=user_loc_array[handover1call_index]           
    if len(dis1)>0:
        rsl1bs1,rsl1bs2=rsl_cal_vec(dis1)
        tmp5=np.where(rsl1bs1<RSL)
        if len(tmp5[0])>0:
            hand12drop=hand12drop+len(tmp5[0])
            handover1call=np.delete(handover1call,tmp5[0])
            handover1call_index=np.delete(handover1call_index,tmp5[0])
            handover1call_duration=np.delete(handover1call_duration,tmp5[0])
    #similarly for handover of BS2 to BS1
    dis2=user_loc_array[handover2call_index]
    if len(dis2)>0:
        rsl2bs,rsl2bs2=rsl_cal_vec(dis2)
        tmp6=np.where(rsl2bs2<RSL)
        if len(tmp6[0])>0:
            hand21drop=hand21drop+len(tmp6[0])
            handover2call=np.delete(handover2call,tmp6[0])
            handover2call_index=np.delete(handover2call_index,tmp6[0])
            handover2call_duration=np.delete(handover2call_duration,tmp6[0])

#fun to determine which users will generate calls
def establish_call():
    #determing how many total users are on call on both BS1 and BS2 
    no_of_users_oncall=len(tch1_index)+len(tch2_index)+len(handover1call_index)+len(handover2call_index)
    #detemining probality for users who are currently not on call
    user_loc_array=np.random.random(NO_OF_USERS-no_of_users_oncall)
    #t4 is array of 0 to number of users on call  (0,1,2,3,4,.....)
    t4=np.arange(no_of_users_oncall)
    #apppending users from all tables (i.e index of all those users who are on call)
    t1=np.append(tch1_index,tch2_index)
    t2=np.append(handover1call_index,handover2call_index)
    t3=np.append(t1,t2)
    #sorting all users index on call
    t3=np.sort(t3)
    #inserting 1 for users who are on call as these users cannot generate new calls
    #insreting at t3-t4 positions to insert these are correct positions
    user_loc_array=np.insert(user_loc_array,t3-t4,1)
    #then finding those users index who will attempt call
    #these is given by all those indexes which is less than call rate
    z=np.where(user_loc_array<(CALL_RATE_CON))
    return z[0].astype(int) #returning index converting to int

def rem_users(swap_places):
    global tch1_call_duration,tch1_index,tch2_index,tch2_call_duration
    global handover1call,handover2call,call_dropped_bs1,call_dropped_bs2
    global handover1call_index,handover2call_index,handover1call_duration,handover2call_duration
    global hand12success,hand21success,hand12drop,hand21drop,call_success_1,call_success_2
    #removing calls (i.e removing table entries) that leave the road and counting them as successful call
    #swap_places is index where user has left the road
    if len(swap_places)>0:
        for swap_places_val in swap_places:
            #checking if this user exists on any of the table
            temp1=np.where(tch1_index==swap_places_val)
            temp2=np.where(tch2_index==swap_places_val)
            temp3=np.where(handover1call_index==swap_places_val)
            temp4=np.where(handover2call_index==swap_places_val)
            #if it is present then removing those entries to free up that channel and counting success call
            if len(temp1[0])>0:
                call_success_1=call_success_1+len(temp1[0])
                tch1_call_duration=np.delete(tch1_call_duration,temp1[0])
                tch1_index=np.delete(tch1_index,temp1[0])
            if len(temp2[0])>0:
                call_success_2=call_success_2+len(temp2[0])
                tch2_call_duration=np.delete(tch2_call_duration,temp2[0])
                tch2_index=np.delete(tch2_index,temp2[0])
            if len(temp3[0])>0:
                call_success_1=call_success_1+len(temp3[0])
                handover1call=np.delete(handover1call,temp3[0])
                handover1call_index=np.delete(handover1call_index,temp3[0])
                handover1call_duration=np.delete(handover1call_duration,temp3[0])
            if len(temp4[0])>0:
                call_success_2=call_success_2+len(temp4[0])
                handover2call=np.delete(handover2call,temp4[0])
                handover2call_index=np.delete(handover2call_index,temp4[0])
                handover2call_duration=np.delete(handover2call_duration,temp4[0])

#function to print the output
def printing(step):
    global listvalues1,listvalues2
    listnames=["Channels in use\t\t\t",
           "Call attempts\t\t\t",
           "Successful call connections\t",
           "Successfully completed calls\t",
           "Handoff attempts\t\t",
           "Successful handoff\t\t",
           "Handoff failure power\t\t",
           "Handoff failure capacity\t",
           "Call drops\t\t\t",
           "Capacity block\t\t\t",
           "Power block\t\t\t"]
    
    #currently occupied channels on each BS
    tch1_used=len(tch1_index)+len(handover1call_index)+len(handover2call_index)
    tch2_used=len(tch2_index)+len(handover2call_index)+len(handover1call_index)
    
    #list of required values at output in order listed in listnames
    #calls drops will be on BS1 will be call dropped at BS1 and also when handover fails while 
    # transfering from BS1 to BS2 due to call drop at that BS
    #calls failed at BS1 will be call failed at BS1 and also when handover fails while transfering
    # from BS2 to BS1 and there is capcity blocked at BS1
    #similar will be case at BS2
    list1=[tch1_used,call_attempted1,call_connected1,call_success_1,hand12attempt,
           hand12success,hand12drop,hand12fail_cap,call_dropped_bs1+hand12drop,call_blocked_cap1+hand21fail_cap,call_blocked_pwr1]
    list2=[tch2_used,call_attempted2,call_connected2,call_success_2,hand21attempt,
           hand21success,hand21drop,hand21fail_cap,call_dropped_bs2+hand21drop,call_blocked_cap2+hand12fail_cap,call_blocked_pwr2]
    
    #if summary is not requested
    if step!="summary":   
        #list values is an 2d array consisting hourly stats in order listed in listnames
        listvalues1[0].append(tch1_used)
        listvalues2[0].append(tch2_used)
        for cnt1 in range(1,11):
            #subtracting sum to remove the stats of all previous hour and only keep stats of that hour
            listvalues1[cnt1].append(list1[cnt1]-sum(listvalues1[cnt1]))
        for cnt2 in range(1,11):
            listvalues2[cnt2].append(list2[cnt2]-sum(listvalues2[cnt2]))
        print("For hour {}".format(step))  
    #for printing the stats
    if step=="summary":
        print("Summary after entire simulation:")
    print("The number of\t\t\tBS1 \tBS2")
    print("-------------------------------------------")
    for cnt in range(len(listnames)):
        if step=="summary":
            print(listnames[cnt],list1[cnt],"\t",list2[cnt])
        else:
            print(listnames[cnt],listvalues1[cnt][step-1],"\t",listvalues2[cnt][step-1])
    print("")

#array of users and its positions initialized
user_loc_array=np.random.random(NO_OF_USERS)*BS_POSITION*1000  #meters
#determining the direction of the users with its speed
#this array holds the speed and direction of all users
#(i.e) a table containing users current distance and speed+direction
user_speed_direction=np.copy(user_loc_array)
user_speed_direction [user_speed_direction<(BS_POSITION*1000)/2] = UE_SPEED
user_speed_direction [user_speed_direction!=UE_SPEED] = -UE_SPEED

#getting shadowing values
shadow1,shadow2=shadowing()

#lists used for printing and storing hourly stats
listvalues1=[[] for _ in range(11)]
listvalues2=[[] for _ in range(11)]
print("")
print("Simulation results:")
print("")
#simulating of the duration mentioned
for i in range (1,T_SIM_TIME*3600+1):
    
    #calling the funtions for managing
    handover()
    oncallusers()    
    possible_usr_call=establish_call()
    #if any user originating calls
    if(len(possible_usr_call)>0):
        #funtion to check if attempted call do actually connect
        check_call(possible_usr_call)
    
    #moving the users in the direction with speed at every step
    user_loc_array=user_loc_array+user_speed_direction
    #when a particular user leaves the road at 0 or at distance of BS2
    swap1=np.where(user_loc_array<=0)
    swap2=np.where(user_loc_array>=(BS_POSITION*1000))
    swap_places=np.append(swap1[0],swap2[0])
    
    #deleteing the users who have left the road and counting as successfull call
    rem_users(swap_places)
    
# To maintain the number of users we can assume new users are 
# 1) Entering from either side of the road
# 2) Entering at any random position on the road
# depending on the above tyoes of simulation needed either
# enable Block 1 or Block 2 respectively below

# BLOCK 1 #####################################################################
##Users entering (at the same index) at either ends of road i.e. at 1m or (BS_POSITION*1000)-1 meter 
##Then updating speed and direction for the new user in the table of user distance and speed
    swap_ele=np.random.randint(2,size=len(swap_places))    
    new_usr_speed=np.copy(swap_ele)
    new_usr_direction=np.copy(swap_ele)
    new_usr_speed [new_usr_speed==0] = UE_SPEED
    new_usr_speed [new_usr_speed==1] = -UE_SPEED
    new_usr_direction [new_usr_direction==1] = (BS_POSITION*1000)-1
    new_usr_direction [new_usr_direction==0] = 1
    #adding these new values in the table at the index where old users leave
    user_loc_array[swap_places]=new_usr_direction
    user_speed_direction[swap_places]=new_usr_speed   
    
# BLOCK 2 #####################################################################
##Users entering (at the same index) at random positions on road 
##Then updating speed and direction for the new user in the table of user distance and speed 
#    swap_ele=np.random.random(len(swap_places))*1000*12
#    new_usr_speed=np.copy(swap_ele)
#    new_usr_direction=np.copy(swap_ele)
#    new_usr_speed [new_usr_speed<(BS_POSITION*1000)/2] = UE_SPEED
#    new_usr_speed [new_usr_speed!=UE_SPEED] = -UE_SPEED
#    #adding these new values in the table at the index where old users leave
#    user_loc_array[swap_places]=new_usr_direction
#    user_speed_direction[swap_places]=new_usr_speed   
    
###############################################################################
    
   #for seeing the user distribution at every 100th iteration
   #uncomment the below block to see users simulation distribution
###############################################################################
#    if (i%100)==0:
#        plt.hist(user_loc_array,bins=100)
#        plt.pause(0000000000000.1)
#        plt.clf()
###############################################################################
   
#    printing at every 1 hour using printing function
    if (i%3600)==0:
        printing(int(i/3600))
        
#printing summary report
printing("summary")
#printing execution time of code
print("Execution time is {} seconds".format(round((time.time() - start),3)))
#for maintaing the output on screen
input("press any key to exit")

## Below are blocks to check the output of rsl function
 
##def to plot output of RSL function of both BS
#def rsl_test():
#    rslbs1=[]
#    rslbs2=[]
#    for i in range (1,11999):
#        rsl_bs1,rsl_bs2=rsl_cal(i)
#        rslbs1.append(rsl_bs1)
#        rslbs2.append(rsl_bs2)
#    iwe=np.arange(1,11999)
#    plt.plot(iwe,rslbs1)
#    plt.plot(iwe,rslbs2)
#    plt.show()
#rsl_test()
##def to plot output of RSL vectorized function of both BS
#def rsl_vec_test():
#    d=np.arange(1,11999)
#    rsl_bs1,rsl_bs2=rsl_cal_vec(d)
#    plt.plot(d,rsl_bs1)
#    plt.plot(d,rsl_bs2)
#    plt.title('RSL distribution')
#    plt.xlabel('distance in meters')
#    plt.ylabel('RSL in dBm')
#    plt.grid(True)
#    plt.show()
#rsl_vec_test()