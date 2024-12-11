#!/usr/bin/env python3
import os,sys,shutil
import re
import datetime
import subprocess
import tempfile


USERNOTALLOWED_ERROR=-10

class TaskScheduler():
	def __init__(self):
		super(TaskScheduler, self).__init__()
		self.dbg=False
	#def __init__

	def _debug(self,msg):
		if (self.dbg):
			print("libtaskscheduler: {}".format(msg))
	#def _debug

	def getUserCron(self):
		userCron={}
		rawCron=[]
		cmdOutput=self._getRawUserCron()
		for line in cmdOutput:
			if not line.strip().startswith("#") and len(line.strip())>1:
				rawCron.append(' '.join(line.split()))
		userCron=self._parseCron(rawCron)
		userCron=self._sortCron(userCron,"restepoch")
		return(userCron)
	#def getUserCron

	def _getRawUserCron(self):
		cmd=["crontab","-l"]
		try:
			cmdOutput=subprocess.check_output(cmd).decode()
		except:
			cmdOutput=[]
		cmdOutput="".join(cmdOutput)
		cmdOutput=cmdOutput.split("\n")
		cmdOutput=[l.strip() for l in cmdOutput]
		return(cmdOutput)
	#def _getRawUserCron

	def getSystemCron(self):
		cronDir="/etc/cron.d"
		sysCron={}
		rawCron=[]
		if os.path.isdir(cronDir)==True:
			for cronFile in os.listdir(cronDir):
				rawCron=[]
				cmdOutput=self._getRawSystemCron(os.path.join(cronDir,cronFile))
				for line in cmdOutput:
					if not line.strip().startswith("#") and len(line.strip())>1:
						rawCron.append(line)
				syscronFile=self._parseCron(rawCron,os.path.join(cronDir,cronFile))
				for key,item in syscronFile.items():
					if key not in sysCron.keys():
						sysCron.update(syscronFile)
					elif sysCron[key]["cmd"]!=item["cmd"]:
						while key in sysCron.keys():
							key+=1
						sysCron.update({key:item})

		sysCron=self._sortCron(sysCron,"restepoch")
		return(sysCron)
	#def getSystemCron

	def _getRawSystemCron(self,cronF):
		lines=[]
		data=[]
		if os.path.isfile(cronF):
			try:
				with open(cronF) as f:
					lines=f.readlines()
			except Exception as e:
				print(repr(e))
				print("Reverting to taskscheduler")
				cronF="/etc/cron.d/taskscheduler"
				with open(cronF) as f:
					lines=f.readlines()

			for l in lines:
				if not l.startswith("#") and len(l)>2 and len(l.split())>6:
						data.append(' '.join(l.split()))

		return data
	#def _getRawSystemCron

	def _sortCron(self,cron,field):
		cronSorted=dict(sorted(cron.items()))
		return (cronSorted)
	#def _sortCron

	def _parseCron(self,rawCron=[],cronF=""):
		cron={}
		for line in rawCron:
			user=""
			line=" ".join(line.split())
			if line.startswith("@"):
				cmd=line
				tdate=datetime.datetime.today() + datetime.timedelta(days=1)
				(m,h,dom,mon,dow)=(tdate.minute,tdate.hour,tdate.day,tdate.month,tdate.weekday())
			else:
				(m,h,dom,mon,dow)=line.split(" ")[0:5]
			timeAt=self._getTimeAtForTask(m,h,dom,mon,dow)
			if len(cronF)>0:
				user=line.split(" ")[5]
				cmd=" ".join(line.split(" ")[6:])
			else:
				cmd=" ".join(line.split(" ")[5:])
			restseconds=self._getRestTime(timeAt)
			rest=str(datetime.timedelta(seconds=restseconds))
			#Ensure restseconds is unique
			while restseconds in cron.keys():
				restseconds+=1
			cron[restseconds]={"next":timeAt,"epoch":int(datetime.datetime.now().timestamp()),"user":user,"rest":rest,"cmd":cmd,"raw":line,"file":cronF}
		return(cron)
	#def _parseCron

	def _getRestTime(self,timeAt):
		now=datetime.datetime.now()	
		(mon,dom,h,m)=int(timeAt[6:8]),int(timeAt[9:11]),int(timeAt[0:2]),int(timeAt[3:5])
		epoch=now.timestamp()
		try:
			epoch=datetime.datetime(now.year,mon,dom,h,m).timestamp()
		except Exception as e:
			print(e)
			print("m: {0} H: {1} D: {2} M: {3}".format(m,h,dom,mon))
			epoch=datetime.datetime(now.year,mon+1,1,h,m).timestamp()

			
		if int(epoch)<int(now.timestamp()):
			epoch=datetime.datetime(now.year+1,mon,dom,h,m).timestamp()
		return(int(epoch-int(datetime.datetime.now().timestamp())))
	#def _getRestTime

	def _getTimeAtForTask(self,m,h,dom,mon,dow):
		rawTime="{0}:{1}".format(h,m)
		rawDate="{0}:{1}".format(mon,dom)
		now = datetime.datetime.now()
		nowTime="{0}:{1}".format(now.hour,now.minute)
		nowDate="{0}:{1}".format(now.month,now.day)
		(nextTime,inc)=self._getNextTime(rawTime,nowTime)
		nextTime=nextTime.zfill(4)
		nextDate=self._getNextDate(rawDate,nowDate,inc).zfill(4)
		compDate="{}{}".format(nowDate.split(":")[0].zfill(2),nowDate.split(":")[1].zfill(2))
		if nextDate!=compDate:
			(nextTime,inc)=self._getNextTime(rawTime,"0:0")
			nextTime=nextTime.zfill(4)
		timeAt=("{0}:{1} {2}-{3}".format(nextTime[0:2],nextTime[2:4],nextDate[0:2],nextDate[2:4]))
		return(timeAt)
	#def _getTimeAtForTask

	def _getNextTime(self,raw,now):
		#Expand regex and select the next
		lines=self._expandCronRegex(raw,24,60,0,now)

		(nowH,nowM)=now.split(":")
		nowM=str(int(nowM)+1)
		if int(nowM)>59:
			nowM="0"
			nowH=str(int(nowH)+1)
			if int(nowH)>23:
				nowH="0"
		nowM=str(nowM).zfill(2)
		nextTime=int("{}{}".format(now.split(":")[0],nowM))
		sw=False
		inc=1
		for line in lines:
			if isinstance(line,str):
				continue
			if line>nextTime:
				inc=0
				nextTime=line
				break
		if inc==1 and len(lines)>0:
			nextTime=lines[0]
		return(str(nextTime),inc)
	#def _getNextTime(self,raw,now):

	def _getNextDate(self,raw,now,inc=0):
		maxdom=0
		(m,d)=now.split(":")
		m=int(m)
		d=int(d)+inc
		if m%2==0 or m==7:
			maxdom=31
		elif m!=1:
			maxdom=30
		else:
			maxdom=28
		if d>maxdom:
			d=1
			m+=1
		lines=self._expandCronRegex(raw,12,maxdom,1,now)
		if m>12:
			m=1
		d=str(d).zfill(2)
		nextDate=int("{}{}".format(m,d))
		sw=False
		for line in lines:
			if line>=nextDate:
				nextDate=line
				sw=True
				break

		if sw==False and len(lines)>0:
			nextDate=lines[0]
		return(str(nextDate))
	#def _getNextDate

	def _expandCronRegex(self,raw,last=0,last2=0,first=0,now=0):
		(data1,data2)=raw.split(":")
		now1=first
		now2=first
		lines=[]
		if not(isinstance(now,int)):
			(now1,now2)=now.split(":")

		if "@" in raw:
			lines.append(data1)
		else:
			selectedData=self._processCronField(data1,first,last,current=now1)
			for data in selectedData:
				selectedData2=self._processCronField(data2,first,last2)
				for item in selectedData2:
					lines.append(int("{0}{1}".format(data.zfill(2),str(item).zfill(2))))
		return(lines)
	#def _expandCronRegex

	def _processCronField(self,cronData,first,last,current=-1):
		selectedData=[]
		for data in cronData.split(","):
			if "-" in data:
				rangedata=data.split("-")
				#Simply generate lines for range.
				#1-10 = 1 line with 1, 1 line with 2...etc..
				#1-10/2= From 1 to 10 each 2 minutes
				#jump=2
				#1 line with 1 jump, 1 line with 2 + jump
				jump=1
				rlimit=rangedata[-1]
				if rlimit.isdigit()==False:
					(rlimit,jump)=rangedata[-1].split("/")
				for i in range(int(rangedata[0]),int(rlimit)+1,int(jump)):
					selectedData.append(str(i))
			elif data.isdigit():
				#Ensure there are no leading 0 while "0" itself is preserved
				selectedData.append(str(int(data)))
			elif data=="*":
				for i in range(first,int(last)+first):
					selectedData.append(str(i))
		return (selectedData)
	#def _processCronField

	def cronFromJson(self,data,orig="",cronF=""):
		ret=False
		if len(data)==0:
			return(ret)
		if str(data[0].get("cmd",""))=="":
			return(ret)
		root=" "
		if len(cronF)>0:
			root=" root "
			cronArray=self._getRawSystemCron(cronF)
		else:
			cronArray=self._getRawUserCron()
		for itemdata in data:
			cron="{0} {1} {2} {3} {4}{5}{6}".format(itemdata.get("m","*"),itemdata.get("h","*"),itemdata.get("dom","*"),itemdata.get("mon","*"),itemdata.get("dow","*"),root,itemdata.get("cmd"))
			self._debug("Adding task to cron {}".format(cronF))
			self._debug("{}".format(cron))
			self._debug("_________________")
			if cron not in cronArray:
				cronArray.append(cron)
		if len(orig)>0:
			if len(cronF)>0:
				cronArray=self._filterCmdFromCronArray(orig,cronF,cronArray)
			else:
				self.removeFromCron(orig,cronArray)
		if len(cronF)>0:
			ret=self.writeSystemCron(cronArray,cronF)
		else:
			ret=self.writeCron(cronArray)
		return(ret)
	#def cronFromJson

	def writeCron(self,cronArray):
		ret=False
		(f,cronFile)=tempfile.mkstemp()
		with open(cronFile,"w") as fh:
			for line in cronArray:
				if len(line.strip())>0:
					fh.writelines("{}\n".format(line))
		cmd=["/usr/bin/crontab",cronFile]
		try:
			proc=subprocess.run(cmd)
			if proc.returncode==0:
				ret=True
		except Exception as e:
			print(repr(e))
			print(cmd)
			ret=False
		return(ret)
	#def writeCron

	def writeSystemCron(self,cronArray,cronF):
		ret=False
		(f,cronTmp)=tempfile.mkstemp()
		with open(cronTmp,"w") as fh:
			for line in cronArray:
				if len(line.strip())>0:
					fh.writelines("{}\n".format(line))
		os.chmod(cronTmp,0o644 )
		cronF=self._getCronPath(cronF)
		cmd=["pkexec","rsync",cronTmp,cronF,"--usermap=*:root"]
		try:
			proc=subprocess.run(cmd)
			if proc.returncode==0:
				ret=True
		except Exception as e:
			print(repr(e))
			print(cmd)
			ret=False
		return(ret)
	#def writeSystemCron

	def removeFromCron(self,schedcmd,cronArray=[]):
		self._debug("Removing from user cron")
		if len(cronArray)==0:
			cronArray=self._getRawUserCron()
		if schedcmd in cronArray:
			self._debug(cronArray.remove(schedcmd))
		self.writeCron(cronArray)
	#def removeFromCron

	def removeFromSystemCron(self,schedcmd,cronF,cronArray=[]):
		self._debug("Removing from system cron file {}".format(cronF))
		cronF=self._getCronPath(cronF)
		cronArray=self._filterCmdFromCronArray(schedcmd,cronF,cronArray)
		if os.path.isfile(cronF):
			self.writeSystemCron(cronArray,cronF)
		else:
			self._debug("{} not found for remove".format(cronF))
	#def removeFromSystemCron

	def _filterCmdFromCronArray(self,schedcmd,cronF,cronArray=[]):
		cronF=self._getCronPath(cronF)
		if os.path.isfile(cronF):
			if len(cronArray)==0:
				cronArray=self._getRawSystemCron(cronF)
			if schedcmd in cronArray:
				self._debug(cronArray.remove(schedcmd))
		return(cronArray)
	#def _filterCmdFromCronArray
	
	def _getCronPath(self,cronF):
		if len(cronF)>0:
			if not os.path.isfile(cronF):
				if os.path.basename(cronF)==cronF:
					cronF=os.path.join("/","etc","cron.d",cronF)
			self._debug("Selected file: {}".format(cronF))
		return(cronF)
	#def _getCronPath

	def getAt(self):
		lines=[]
		dictTaskId={}
		cmd="atq"
		cmdOutput=subprocess.check_output(cmd).decode()
		days=["mon","tue","wed","thu","fri","sat","sun"]
		months=["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
		for line in cmdOutput.split("\n"):
			line=' '.join(line.split())
			if len(line)>0:
				#[0]=id [1]=Dow [2]=Mon [3]=Dom [4]=h:m:s [5]=y [6]=at queue [7]=user
				data=line.split()
				atid=data[0]
				cmd=self._getCmdForAtTask(atid)
				dow=days.index(data[1].lower())
				mon=months.index(data[2].lower())+1
				dom=data[3]
				h=data[4].split(":")[0]
				m=data[4].split(":")[1]
				lines.append("{0} {1} {2} {3} * {4}".format(m,h,dom,mon,cmd))
				raw="{0}{1}{2}{3}*{4}".format(m,h,dom,mon,cmd)
				raw=raw.replace(" ","")
				dictTaskId[raw]=atid
		userAt=self._parseCron(lines)
		for key,task in userAt.items():
			raw=task.get("raw").replace(" ","")
			atid=dictTaskId.get(raw,"not found")
			task['atid']=atid
		userAt=self._sortCron(userAt,"restepoch")
		return(userAt)
	#def getAt(self)

	def _getCmdForAtTask(self,atid):
		task="AT Index: {}".format(atid)
		cmd=["at","-c",atid]
		cmdOutput=[]
		try:
			cmdOutput=str(subprocess.check_output(cmd).decode()).split("\n")
		except:
			print("TaskID: {} error getting cmd".format(atid))
		else:
			try:
				pos=cmdOutput.index("}")
			except:
				print("TaskID: {} error getting cmd".format(atid))
				print("POS: {}".format(pos))
			else:
				task=" ".join(cmdOutput[pos+1:])
		return(task)
	#def _getCmdForAtTask

	def removeFromAt(self,atid):
		cmd=["atrm",atid]
		subprocess.run(cmd)
	#def removeFromAt

	def addAtJob(self,m,h,dom,mon,task):
		ret=True
		now=datetime.datetime.now()
		year=now.year
		schedTime="{}{}{}{}".format(str(mon).zfill(2),str(dom).zfill(2),str(h).zfill(2),str(m).zfill(2))
		nowTime="{}{}{}{}".format(str(now.month).zfill(2),str(now.day).zfill(2),str(now.hour).zfill(2),str(now.minute).zfill(2))
		if schedTime<=nowTime:
			year+=1
		#If we want to have a command name then we must schedule it through echo and pipe
		cmd=["at","{}:{}".format(str(h).zfill(2),str(m).zfill(2)),"{}.{}.{}".format(dom,mon,year)]
		try:
			cmdEcho = subprocess.Popen(('echo', task), stdout=subprocess.PIPE)
		except:
			ret=False
		try:
			output = subprocess.check_output(cmd, stdin=cmdEcho.stdout)
		except:
			ret=False
		cmdEcho.wait()
		return(ret)
	#def addToAt
#class TaskScheduler

