#!/usr/bin/python3
#
#    proxychecker.py is a multithreaded hitfaker and proxychecker
#
#    Copyright (C) 2014 by Jan Helbling <jan.helbling@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from urllib.request import build_opener,ProxyHandler,urlopen,URLError
from gzip import open as gzip_open
from http.client import IncompleteRead,BadStatusLine
from os import path
from sys import stderr,stdout,stdin,exit,platform
from gettext import bindtextdomain,textdomain,gettext as _

if path.exists('/usr/share/locale/de/LC_MESSAGES/proxychecker.mo'):
	bindtextdomain('proxychecker', '/usr/share/locale')
	textdomain('proxychecker')
elif path.exists('/share/locale/de/LC_MESSAGES/proxychecker.mo'):
	bindtextdomain('proxychecker', '/share/locale')
	textdomain('proxychecker')

if 'win' in platform:
	stderr.write(_(' [ERROR] fork could not be imported from os, this programm is not for Windows-Users!!\n'))
	stderr.write(_('        (Windows has no syscall named fork()...\n'))
	stderr.write(_('        You must Upgrade to Linux to use this ;)\n'))
	exit(1)

if 'unixware7' in platform:
	try:
		from os import fork1 as fork
	except ImportError:
		from os import fork
else:
	from os import fork

from os import waitpid,unlink,devnull,WEXITSTATUS

from socket import timeout
from random import randint
from time import time

from ProxyChecker.useragent import *
from ProxyChecker.color import *
from ProxyChecker.regex import *

class proxychecker:
	"""A advanced Proxychecker/Hitfaker in Python"""
	def __init__(self,in_file,out_file,testsite,to,process_num,contains,referer,browserstring,postdata,cookie,color,header):
		"""Run's the program"""
		global RED,REDBOLD,GREEN,GREENBOLD,YELLOW,NOCOLOR
		if header != "":
			if header.count(':') != 1:
				stderr.write(_('{0}[ERROR] --header should exactly contains one ":" !!!{1}').format(RED,NOCOLOR))
				exit(1)
			self.header		=	(header.split(':')[0],header.split(':')[1])
		else:
			self.header		=	('','')
		self.color		=	color.lower()
		self.cookie             =       cookie
		self.postdata           =       postdata.encode('utf-8','ignore')
		self.browserstring      =       browserstring.lower()
		self.referer            =       referer
		self.to                 =       to
		self.testsite           =       testsite
		if not self.testsite.lower().startswith('http://'):			# check if testsite starts with http://, if not
			self.testsite   =       'http://{}'.format(self.testsite)	# add http:// before the testsite
		self.contains           =       contains
		self.process_num        =       process_num
		self.cnt                =       0
		self.totalcnt		=	0
		self.from_url		=	False
		if self.color == 'none':
			RED 		= ''
			REDBOLD		= ''
			GREEN 		= ''
			GREENBOLD	= ''
			YELLOW		= ''
			NOCOLOR		= ''
		
		self.__open_files(in_file,out_file)
		
		if not self.from_url:
			print(_('{0}[INFO] Remove invalid lines from list...').format(YELLOW),end='')
			self.__remove_empty_lines()
			print(_('{0}..[DONE, {1} lines removed]{2}').format(GREEN,self.invalid_line_counter,NOCOLOR))
		
		self.totalproxys	=	len(self.proxys)
		print(_('{0}[TOTAL: {1} Proxys]{2}').format(YELLOW,self.totalproxys,NOCOLOR))
		
		if self.totalproxys == 0:
			stderr.write(_('{0} [ERROR] no proxys found...{1}\n').format(RED,NOCOLOR))
			if out_file == devnull:
				exit(1)
			stderr.write(_('{0} [Remove outputfile]...').format(YELLOW))
			try:
				unlink(out_file)
				stderr.write(_('...{0}[DONE]{1}\n').format(GREEN,NOCOLOR))
			except IOError as e:
				stderr.write(_('...{0}[FAIL]{1}\n').format(RED,NOCOLOR))
				stderr.write(_('{0} [ERROR] While removing {1}: {2}{3}\n').format(RED,e.filename,e.strerror,NOCOLOR))
			exit(1)
		
		print(_('{0}[INFO] ({1}working{0})=(current/total){2}').format(YELLOW,GREEN,NOCOLOR))
		
		# Calling the Main-Function
		self.__main()
	
	def __open_files(self,in_file,out_file):
		try:
                        # Open (and read) the proxylist to be checked and the outputfile
                        if in_file not in ['-','/dev/stdin'] and not in_file.startswith('http://'):
                                if in_file.lower().endswith('.gz'):
                                        self.in_file    =       gzip_open(in_file,'rb')
                                else:
                                        self.in_file    =       open(in_file,'rb')
                                self.proxys     =       self.in_file.readlines()
                                self.in_file.close()
                        elif in_file.startswith('http://'):
                                print(_('{0}[INFO] gather proxys from url...').format(YELLOW),end='')
                                self.from_url   =       True
                                self.fd         =	urlopen(in_file)
                                self.content    =       (self.fd.read()).decode('utf-8','ignore')
                                self.fd.close()
                                self.proxys     =       proxyregex.findall(self.content)
                                print(_('...{0}[DONE, {1} proxys found]{2}').format(GREEN,len(self.proxys),NOCOLOR))
                        else:
                                self.proxys     =       stdin.readlines()
                        if out_file not in [devnull,'/dev/stdout','/dev/stderr','/dev/stdin']:
                                self.__check_for_old_files(out_file)    # check if the out_file already exists
                        if out_file in ['/dev/stdout','-']:
                                self.out_file   =       open('/dev/stdout','w')
                                self.devnull    =       open(devnull,'w')
                                stdout      =       self.devnull
                                stdin       =       self.out_file
                        else:
                                self.out_file   =       open(out_file,'w')
		except URLError as e:
                        print(_('...{0}[FAIL]{1}').format(RED,NOCOLOR))
                        if type(e.args[0]) == str:
                                stderr.write(_('{0} [ERROR] couldn\'t open {1}: {2}{3}\n').format(RED,in_file,e.args[0],NOCOLOR))
                        else:
                                stderr.write(_('{0} [ERROR] couldn\'t open {1}:  {2}{3}\n').format(RED,in_file,e.args[0].strerror,NOCOLOR))
                        exit(1)
		except IOError as e:
                        if type(e.args[0]) == str:
                                stderr.write(_('{0} [ERROR] {1}').format(RED,e.args[0]))
                        else:
                                stderr.write(_('{0} [ERROR] {1}: {2}\n').format(RED,e.filename,e.strerror))
                        exit(1)
	
	def __remove_empty_lines(self):
		"""Remove empty/invalid nonproxys from the list."""
		self.invalid_line_counter	=	len(self.proxys)
		self._proxys			=	[]
		for proxy in self.proxys:
			if type(proxy) != str:
				proxy	=	proxy.decode('utf-8','ignore')
			proxy		=	proxyregex.findall(proxy)
			if proxy != []:
				self._proxys.append(proxy[0])
		self.proxys			=	self._proxys
		del self._proxys
		self.invalid_line_counter	=	self.invalid_line_counter - len(self.proxys)
	
	def __check_for_old_files(self,out_file):
		"""Checks if the path "out_file" exists, if true, then compress it to a gzipped archive with the next number."""
		if path.exists(out_file):
				self.i  =       0
				while True:
					self.filename   =       '{0}.{1}.gz'.format(out_file,self.i)
					if not path.exists(self.filename):
						print(_('{0}[INFO] Compressing {1} in {2} => ').format(YELLOW,out_file,self.filename),end='')
						try:
							self.gzfd       =       gzip_open(self.filename,'wb',9)
							self.fd         =       open(out_file,'rb')
							self.gzfd.write(self.fd.read())
							self.gzfd.close()
							self.fd.close()
							unlink(out_file)
							print(_('{0}[DONE]{1}').format(GREEN,NOCOLOR))
							break
						except IOError as e:
							print(_('{0}[FAIL]{1}').format(RED,NOCOLOR))
							stderr.write(_('{0} [ERROR] with file {1}: {2}{3}\n').format(RED,e.filename,e.strerror,NOCOLOR))
							exit(1)
					self.i          =       self.i + 1
	
	def __check_proxy(self,proxy):
		"""Checks a proxy and save it to file, if the string "contains" is in content, returns true if Success,false on fail"""
		proxyhdl	=	ProxyHandler({'http':proxy})
		opener		=	build_opener(proxyhdl) # Build a opener with the proxy
		if self.browserstring == 'desktop': #check if browserstring is desktop,mobile or all, add the Cookie if set
			opener.addheaders	=	[('Referer',self.referer),('User-Agent',useragent[randint(0,len(useragent)-1)]),('Cookie',self.cookie),(self.header[0],self.header[1])] #Add User-Agent (and Headers/Cookies if set)
		elif self.browserstring == 'mobile':
			opener.addheaders	=	[('Referer',self.referer),('User-Agent',useragent_mobile[randint(0,len(useragent_mobile)-1)]),('Cookie',self.cookie),(self.header[0],self.header[1])]
		else:
			opener.addheaders	=	[('Referer',self.referer),('User-Agent',useragent_all[randint(0,len(useragent_all)-1)]),('Cookie',self.cookie),(self.header[0],self.header[1])]
		try:
			starttime	=	time()
			if self.postdata == b'':
				fd	=	opener.open(self.testsite,timeout=self.to)
			else:
				fd		=	opener.open(self.testsite,timeout=self.to,data=self.postdata) # Open the website, with timeout to and postdata
			content		=	fd.read()
			endtime		=	time()
			contenttype	=	fd.getheader('Content-Type')
			content		=	content.decode('utf-8','ignore')
			fd.close()
			endtime		=	(endtime-starttime).__round__(3)
			if self.contains in content: #Check if the string contains is in content, if true
				print(_('{0}[OK]  \t=>{1}({0}{2}{1})=({3}/{4})          {0}{5}\t-->{6}sec.{7}').format(GREEN,YELLOW,self.cnt+1,self.totalcnt,self.totalproxys,proxy,endtime,NOCOLOR))
				self.__save_proxy(proxy)	# write proxy to file
				return True
			else:				# else, fail
				if (contenttype == 'text/plain' or contenttype == 'text/html') and len(content) < 30:
					print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->Doesnt contain the String: {7}{8}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,content,NOCOLOR))
				else:
					print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->Doesnt contain the String!{7}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,NOCOLOR))
		except IOError as e:
			if e.strerror != None:
				print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->{7}{8}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,e.strerror,NOCOLOR))
			else:
				if hasattr(e,'reason'):
					if type(e.reason) == str:
						print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->{7}{8}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,e.reason,NOCOLOR))
					elif type(e.reason.args) == tuple:
						if e.reason.args[0] == 'timed out':
							print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->Timed Out{7}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,NOCOLOR))
						elif hasattr(e.reason,'strerror'):
							print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->{7}{8}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,e.reason.strerror,NOCOLOR))
						else:
							print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->{7}{8}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,e.reason.args[0],NOCOLOR))
					else:
						print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->{7}{8}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,e.reason,NOCOLOR))
				elif type(e) == timeout:
					print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->Timed Out{7}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,NOCOLOR))
				elif hasattr(e,'args') and not hasattr(e,'reason'):
					if type(e.args[0]) == str:
						print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->{7}{8}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,e.args[0],NOCOLOR))
					else:
						print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->{7}{8}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,e.args[0].strerror,NOCOLOR))
				else:
					print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->{7}{8}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,totalproxys,proxy,str(e),NOCOLOR))
		except BadStatusLine:
			print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->BadStatusLine{7}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,NOCOLOR))
		except IncompleteRead:
			print(_('{0}[FAIL]\t=>{1}({2}{3}{1})=({4}/{5})          {0}{6}\t-->IncompleteRead{7}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,NOCOLOR))
		except KeyboardInterrupt:	# [CTRL] + [C]
			print(_('{0}[ABORTED CTRL+C]     =>{1}({2}{3}{1})=({4}/{5}) {0}{6}\t-->Interrupted by User{7}').format(RED,YELLOW,GREEN,self.cnt,self.totalcnt,self.totalproxys,proxy,NOCOLOR))
		return False
	
	def __save_proxy(self,proxy):
		"""Save the proxy to file."""
		self.out_file.write('{}\n'.format(proxy))
		self.out_file.flush()
	
	def __main(self):
		"""Main, the main-programm"""
		pids = []
		for proxy in self.proxys:
			self.totalcnt	=	self.totalcnt + 1
			pids.append(fork()) # man fork
			if not pids[-1]:
				if self.__check_proxy(proxy):
					exit(0)
				exit(1)
			if len(pids) == self.process_num:
				for pid in pids:
					try:
						(_pid,st)	=	waitpid(pid,0)	# man/pydoc3 (os.) waitpid
						if WEXITSTATUS(st) == 0:
							self.cnt=	self.cnt + 1
					except KeyboardInterrupt:
						exit(1)
				pids = []
		for pid in pids:
			try:
				(_pid,st)	=	waitpid(pid,0) 	# get the exit_code from the forked subproccess
				if WEXITSTATUS(st) == 0:		# if it's 0, __check_proxy has returned true
					self.cnt=       self.cnt + 1 	# incerase the counter
			except KeyboardInterrupt:
				exit(1)
		self.out_file.close()
		if self.cnt == 0:
			print(_('{0}[!!!EPIC FAIL!!!] None of {1} proxys we have checked are working...{2}').format(REDBOLD,self.totalproxys,NOCOLOR))
			if self.out_file.name == devnull:
				exit(0)
			print(_('{0}removing the output-file...{2}').format(REDBOLD,NOCOLOR),end='')
			try:
				unlink(self.out_file.name)
				print(_('{0}...{1}[OK]{2}').format(REDBOLD,GREEN,NOCOLOR))
			except IOError as e:
				print(_('{0}...[FAIL]{1}').format(RED,NOCOLOR))
				stderr.write(_(' [ERROR] Couldn\'t remove {0}: {1}\n').format(e.filename,e.strerror))
				exit(1)
		else:
			print(_('{0}[!!!DONE!!!] {1} of {2} proxys we have checked are working!{3}').format(GREENBOLD,self.cnt,self.totalproxys,NOCOLOR))
			print(_('{0}[New Proxylist saved to => {1}]{2}').format(GREEN,self.out_file.name,NOCOLOR))
		exit(0)
