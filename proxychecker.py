#!/usr/bin/python3
#
# (C) 2013 by Jan Helbling
# jan.helbling@gmail.com
# License: GNU/GPLv3 or newer http://www.gnu.org/licenses/gpl-3.0.txt
# Comment: Just another ProxyChecker in Python
# THIS PROGRAMM IS FREE SOFTWARE (GNU/GPLv3)
#

import urllib.request
import http.client
from os import fork,wait
from optparse import OptionParser

from sys import exc_info,exit,argv
from socket import timeout

import random

useragent = ["Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)",
	"Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 5.1; SLCC1; .NET CLR 1.1.4322)",
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:25.0) Gecko/20100101 Firefox/25.0",
	"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:21.0) Gecko/20100101 Firefox/21.0",
	"Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/24.0",
	"Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36",
	"Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36",
	"Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Version/12.14",
	"Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; de) Presto/2.9.168 Version/11.52",
	"Lynx/2.8.8dev.3 libwww-FM/2.14 SSL-MM/1.4.1"]

class proxychecker:
	"""Another Proxychecker in Python"""
	def __init__(self,in_file,out_file,testsite,to,process_num,contains,referer):
		"""Run's the programm."""
		try:
			# Open the proxylist to be checked and the outputfile
			self.in_file	=	open(in_file,"rb")
			self.proxys	=	self.in_file.readlines()
			self.out_file	=	open(out_file,"w")
		except IOError as e:
			print(exc_info()[1])
			exit(1)
		
		self.referer		=	referer
		self.to			=	to
		self.testsite		=	testsite
		if not self.testsite.lower().startswith("http://"):
			self.testsite	=	"http://" + self.testsite
		self.contains		=	contains
		self.process_num	=	process_num
		# Calling the Main-Function
		self.main()
	
	def check_proxy(self,proxy):
		"""Checks a proxy and save it to file, if the string "contains" is in content."""
		proxy		=	proxy.rstrip("\r\n ") # remove \r\n from the line
		proxyhdl	=	urllib.request.ProxyHandler({'http':proxy})
		opener		=	urllib.request.build_opener(proxyhdl) # Build a opener with the proxy
		opener.addheaders	=	[('Referer',self.referer),('User-Agent',useragent[random.randint(0,9)])]
		
		try:
			fd	=	opener.open(self.testsite,timeout=self.to) # Open the website, with timeout to
			content	=	(fd.read()).decode("utf-8","replace") # reads the content and decode it
			fd.close()
			if self.contains in content: #Check if the string contains is in content, if true
				print("[OK]",proxy)
				self.save_proxy(proxy) # write proxy to file
		except IOError as e:
			print("[FAIL]",proxy)
		except http.client.BadStatusLine as e:
			print("[FAIL]",proxy)
		except http.client.IncompleteRead as e:
			print("[FAIL]",proxy)
		except KeyboardInterrupt as e:
			print("[ABORTED CTRL+C]",proxy)
	
	def save_proxy(self,proxy):
		"""Save the proxy to file."""
		self.out_file.write(proxy+"\n")
		self.out_file.flush()
	
	def main(self):
		"""Main"""
		cnt = 0
		for proxy in self.proxys:
			if not fork(): # man fork
				self.check_proxy(proxy.decode("utf-8","replace"))
				exit(0)
			cnt = cnt + 1
			if cnt == self.process_num:
				for i in range(self.process_num):
					try:
						wait() # man wait
					except KeyboardInterrupt as e:
						exit(1)
				cnt = 0
		self.in_file.close()
		self.out_file.close()

if __name__ == "__main__":
	if len(argv) < 2:
		print("Invalid number of arguments! Use -h for options.")
		exit(0)
	# Parse options and run the proxychecker
	parser = OptionParser()
	parser.add_option("-i", "--input", dest="input",help="read proxys from file", metavar="FILE")
	parser.add_option("-o", "--output", dest="output",help="write proxys to file, default: checked_proxys.txt", metavar="FILE",default="checked_proxys.txt")
	parser.add_option("-u", "--testsite", dest="testsite",help="use this site for requests, default http://www.gnu.org", metavar="WEBSITE",default="http://www.gnu.org")
	parser.add_option("-c", "--contains", dest="contains",help="good hit must contains, default GNU", metavar="STRING",default="GNU")
	parser.add_option("-t", "--timeout", dest="to",help="timeout, default 5.0", metavar="TIMEOUT",type="float",default=5.0)
	parser.add_option("-p", "--process", dest="numproc",help="number of processes, default 10", type="int",metavar="NUM",default=10)
	parser.add_option("-r", "--referer", dest="referer",help="Use this site as referer, default \"\"",metavar="REFERER",default="")
	(options, args) = parser.parse_args()
	p = proxychecker(options.input,options.output,options.testsite,options.to,options.numproc,options.contains,options.referer)
