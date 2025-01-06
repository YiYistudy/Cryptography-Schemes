import os
from sys import exit, getsizeof
from base64 import b64encode, b64decode
from time import time
try:
	from psutil import Process
except:
	print("Cannot compute the memory via ``psutil.Process``. ")
	print("Please try to install the ``psutil`` library via ``python -m pip install psutil`` or ``apt-get install python3-psutil``. ")
	print("Please press the enter key to exit. ")
	input()
	exit(-1)
try:
	from charm.toolbox.pairinggroup import PairingGroup, G1, ZR, pair, pc_element as Element
except:
	print("The environment of the ``charm`` library is not handled correctly. ")
	print("See https://blog.csdn.net/weixin_45726033/article/details/144254189 in Chinese if necessary. ")
	print("Please press the enter key to exit. ")
	input()
	exit(-1)
try:
	os.chdir(os.path.abspath(os.path.dirname(__file__)))
except:
	pass
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EOF = (-1)


class SchemeIBME:
	def __init__(self:object, group:None|PairingGroup = None) -> object:
		self.__group = group if isinstance(group, PairingGroup) else PairingGroup("SS512", secparam = 512)
		if self.__group.secparam < 1:
			self.__group = PairingGroup(self.__group.groupType())
			print("Init: The securtiy parameter should be a positive integer but it is not, which has been defaulted to {0}. ".format(self.__group.secparam))
		self.__operand = (1 << self.__group.secparam) - 1 # use to cast binary strings
		self.__mpk = None
		self.__msk = None
		self.__flag = False # to indicate whether it has already set up
	def Setup(self:object) -> tuple: # $\textbf{Setup}() \rightarrow (\textit{mpk}, \textit{msk})$
		# Check #
		self.__flag = False
		
		# Scheme #
		r, s = self.__group.random(ZR), self.__group.random(ZR) # generate $r, s \in \mathbb{Z}_p^*$ randomly
		P = self.__group.random(G1) # generate $P \in \mathbb{G}_1$ randomly
		P0 = r * P # $P_0 \gets r \cdot P$
		H = lambda x:self.__group.hash(x, G1) # $H_1:\mathbb{Z}_p^* \rightarrow \mathbb{G}_1$
		mask = bytes.fromhex("ed27dbfb02752e0e16bc4502d6c732bc5f1cc92ba19b2d93a4e95c597ca42753e93550b52f82b6c13fb8cc0c2fc64487")
		HPrime = lambda x:self.__group.hash(bytes([ a ^ b for (a, b) in zip(self.__group.serialize(x), mask)]), G1) # $H':\mathbb{Z}_p^* \oplus \textit{mask} \rightarrow \mathbb{G}_1$
		self.__mpk = (P, P0, H, HPrime) # $\textit{mpk} \gets (P, P_0, H, H')$
		self.__msk = (r, s) # $\textit{msk} \gets (r, s)$
		
		# Return #
		self.__flag = True
		return (self.__mpk, self.__msk) # $\textbf{return }(\textit{mpk}, \textit{msk})$
	def SKGen(self:object, sender:Element) -> Element: # $\textbf{SKGen}(S) \rightarrow \textit{ek}_S$
		# Check #
		if not self.__flag:
			self.Setup()
			print("SKGen: The ``Setup`` procedure has not been called yet. The program will call the ``Setup`` first and finish the ``SKGen`` subsequently. ")
		if isinstance(sender, Element) and sender.type == ZR: # type check
			S = sender
		else:
			S = self.__group.random(ZR)
			print("SKGen: The variable $S$ should be an element of $\\mathbb{Z}_p^*$ but it is not, which has been generated randomly. ")
		
		# Unpack #
		HPrime = self.__mpk[-1]
		s = self.__msk[1]
		
		# Scheme #
		ek_S = s * HPrime(S) # $\textit{ek}_S \gets s \cdot H'(S)$
		
		# Return #
		return ek_S # $textbf{return }\textit{ek}_S$
	def RKGen(self:object, receiver:Element) -> Element: # $\textbf{SKGen}(S) \rightarrow \textit{dk}_R$
		# Check #
		if not self.__flag:
			self.Setup()
			print("RKGen: The ``Setup`` procedure has not been called yet. The program will call the ``Setup`` first and finish the ``RKGen`` subsequently. ")
		if isinstance(receiver, Element) and receiver.type == ZR: # type check
			R = receiver
		else:
			R = self.__group.random(ZR)
			print("RKGen: The variable $R$ should be an element of $\\mathbb{Z}_p^*$ but it is not, which has been generated randomly. ")
		
		# Unpack #
		H = self.__mpk[-2]
		r, s = self.__msk
		
		# Scheme #
		H_R = H(R) # $H_R \gets H(R)$
		dk1 = r * H_R # $\textit{dk}_1 \gets r \cdot H_R$
		dk2 = s * H_R # $\textit{dk}_2 \gets s \cdot H_R$
		dk3 = H_R # $\textit{dk}_3 \gets H_R$
		dk_R = (dk1, dk2, dk3) # $\textit{dk}_R \gets (\textit{dk}_1, \textit{dk}_2, \textit{dk}_3)$
		
		# Return #
		return dk_R # $textbf{return }\textit{dk}_R$
	def Enc(self:object, ekS:Element, receiver:Element, message:int|bytes) -> tuple: # $\textbf{Enc}(\textit{ek}_S, R, M) \rightarrow C$
		# Check #
		if not self.__flag:
			self.Setup()
			print("Enc: The ``Setup`` procedure has not been called yet. The program will call the ``Setup`` first and finish the ``Enc`` subsequently. ")
		if isinstance(ekS, Element):
			ek_S = ekS
		else:
			ek_S = self.SKGen(self.__group.random(ZR))
			print("Enc: The variable $\\textit{ek}_S$ should be an element but it is not, which has been generated randomly. ")
		if isinstance(receiver, Element) and receiver.type == ZR: # type check
			R = receiver
		else:
			R = self.__group.random(ZR)
			print("Enc: The variable $R$ should be an element of $\\mathbb{Z}_p^*$ but it is not, which has been generated randomly. ")
		if isinstance(message, int): # type check
			M = message & self.__operand
			if message != M:
				print("Enc: The passed message (int) is too long, which has been cast. ")
		elif isinstance(message, bytes):
			M = int.from_bytes(message, byteorder = "big") & self.__operand
			if len(message) << 3 > self.__group.secparam:
				print("Enc: The passed message (bytes) is too long, which has been cast. ")
		else:
			M = int.from_bytes(b"SchemeIBME", byteorder = "big") & self.__operand
			print("Enc: The variable $M$ should be an integer or a ``bytes`` object but it is not, which has been defaulted to b\"SchemeIBME\". ")
		
		# Unpack #
		H = self.__mpk[-2]
		P, P0 = self.__mpk[0], self.__mpk[1]
		
		# Scheme #
		u, t = self.__group.random(ZR), self.__group.random(ZR) # generate $u, t \in \mathbb{Z}_p^*$ randomly
		T = t * P # $T \gets t \cdot P$
		U = u * P # $U \gets u \cdot P$
		H_R = H(R) # $H_R \gets H(R)$
		k_R = pair(H_R, u * P0) # $k_R \gets e(H_R, u \cdot P_0)$
		k_S = pair(H_R, T + ek_S) # $k_S \gets e(H_R, T + \textit{ek}_S)$
		V = M ^ int.from_bytes(self.__group.serialize(k_R), byteorder = "big") ^ int.from_bytes(self.__group.serialize(k_S), byteorder = "big") # $V \gets M \oplus k_R \oplus k_S$
		C = (T, U, V) # $C \gets (T, U, V)$
		
		# Return #
		return C # $\textbf{return }C$	
	def Dec(self:object, dkR:tuple, sender:Element, cipher:tuple) -> int: # $\textbf{Dec}(\textit{dk}_R, S, C) \rightarrow M$
		# Check #
		if not self.__flag:
			self.Setup()
			print("Dec: The ``Setup`` procedure has not been called yet. The program will call the ``Setup`` first and finish the ``Dec`` subsequently. ")
		if isinstance(dkR, tuple) and len(dkR) == 3 and all([isinstance(ele, Element) for ele in dkR]): # hybrid check
			dk_R = dkR
		else:
			dk_R = self.RKGen(self.__group.random(ZR))
			print("Dec: The variable $\\textit{dk}_R$ should be a tuple containing 3 elements but it is not, which has been generated randomly. ")
		if isinstance(sender, Element) and sender.type == ZR: # type check
			S = sender
		else:
			S = self.__group.random(ZR)
			print("Dec: The variable $S$ should be an element of $\\mathbb{Z}_p^*$ but it is not, which has been generated randomly. ")
		if isinstance(cipher, tuple) and len(cipher) == 3 and isinstance(cipher[0], Element) and isinstance(cipher[1], Element) and isinstance(cipher[2], int): # hybrid check
			C = cipher
		else:
			C = self.Enc(self.SKGen(self.__group.random(ZR)), self.__group.random(ZR), b"SchemeIBME")
			print("Dec: The variable $C$ should be a tuple containing 2 elements and an ``int`` object but it is not, which has been generated randomly. ")
		
		# Unpack #
		HPrime = self.__mpk[-1]
		dk1, dk2, dk3 = dk_R
		T, U, V = C
		
		# Scheme #
		k_R = pair(dk1, U) # $k_R \gets e(\textit{dk}_1, U)$
		HPrime_S = HPrime(S) # $H'_S \gets H'(S)$
		k_S = pair(dk3, T) * pair(HPrime_S, dk2) # $k_S \gets e(\textit{dk}_3, T)$
		M = V ^ int.from_bytes(self.__group.serialize(k_R), byteorder = "big") ^ int.from_bytes(self.__group.serialize(k_S), byteorder = "big") # $M \gets V \oplus k_R \oplus k_S$
		
		# Return #
		return M # $\textbf{return }M$


def Scheme(curveType:tuple|list|str, round:int = None) -> list:
	# Begin #
	try:
		if isinstance(curveType, (tuple, list)) and len(curveType) == 2 and isinstance(curveType[0], str) and isinstance(curveType[1], int):
			if curveType[1] >= 1:
				group = PairingGroup(curveType[0], secparam = curveType[1])
			else:
				group = PairingGroup(curveType[0])
		else:
			group = PairingGroup(curveType)
	except:
		if isinstance(curveType, (tuple, list)) and len(curveType) == 2 and isinstance(curveType[0], str) and isinstance(curveType[1], int):
			print("curveType =", curveType[0])
			if curveType[1] >= 1:
				print("secparam =", curveType[1])
		elif isinstance(curveType, str):
			print("curveType =", curveType)
		if isinstance(round, int) and round >= 0:
			print("round =", round)
		print("Is the system valid? No. {0}. ".format(e))
		return (																																														\
			([curveType[0], curveType[1]] if isinstance(curveType, (tuple, list)) and len(curveType) == 2 and isinstance(curveType[0], str) and isinstance(curveType[1], int) else [(curveType if isinstance(curveType, str) else None), None])		\
			+ [round if isinstance(round, int) else None] + [False] * 2 + [-1] * 13																																	\
		)
	process = Process(os.getpid())
	print("curveType =", group.groupType())
	print("secparam =", group.secparam)
	if isinstance(round, int) and round >= 0:
		print("round =", round)
	print("Is the system valid? Yes. ")
	
	# Initialization #
	schemeIBME = SchemeIBME(group)
	timeRecords, memoryRecords = [], []

	# Setup #
	startTime = time()
	mpk, msk = schemeIBME.Setup()
	endTime = time()
	timeRecords.append(endTime - startTime)
	memoryRecords.append(process.memory_info().rss)
	
	# SKGen #
	startTime = time()
	S = group.random(ZR)
	ek_S = schemeIBME.SKGen(S)
	endTime = time()
	timeRecords.append(endTime - startTime)
	memoryRecords.append(process.memory_info().rss)
	
	# RKGen #
	startTime = time()
	R = group.random(ZR)
	dk_R = schemeIBME.RKGen(R)
	endTime = time()
	timeRecords.append(endTime - startTime)
	memoryRecords.append(process.memory_info().rss)
	
	# Enc #
	startTime = time()
	message = int.from_bytes(b"SchemeIBME", byteorder = "big")
	C = schemeIBME.Enc(ek_S, R, message)
	endTime = time()
	timeRecords.append(endTime - startTime)
	memoryRecords.append(process.memory_info().rss)
	
	# Dec #
	startTime = time()
	M = schemeIBME.Dec(dk_R, S, C)
	endTime = time()
	timeRecords.append(endTime - startTime)
	memoryRecords.append(process.memory_info().rss)
	
	# End #
	sizeRecords = [getsizeof(ek_S), getsizeof(dk_R), getsizeof(C)]
	del schemeIBME
	print("Original:", message)
	print("Decrypted:", M)
	print("Is the scheme correct (message == M)? {0}. ".format("Yes" if message == M else "No"))
	print("Time:", timeRecords)
	print("Memory:", memoryRecords)
	print("Size:", sizeRecords)
	print()
	return [group.groupType(), group.secparam, round if isinstance(round, int) else None, True, message == M] + timeRecords + memoryRecords + sizeRecords

def handleFolder(fd:str) -> bool:
	folder = str(fd)
	if not folder:
		return True
	elif os.path.exists(folder):
		return os.path.isdir(folder)
	else:
		try:
			os.makedirs(folder)
			return True
		except:
			return False

def main() -> int:
	# Begin #
	curveTypes = (("SS512", 128), ("SS512", 160), ("SS512", 224), ("SS512", 256), ("SS512", 384), ("SS512", 512))
	roundCount, filePath = 20, "SchemeIBME.xlsx"
	columns = [															\
		"curveType", "secparam", "roundCount", 								\
		"isSystemValid", "isSchemeCorrect", 									\
		"Setup (s)", "SKGen (s)", "RKGen (s)", "Enc (s)", "Dec (s)", 			\
		"Setup (B)", "SKGen (B)", "RKGen (B)", "Enc (B)", "Dec (B)", 		\
		"ek_S (B)", "dk_R (B)", "C (B)"										\
	]
	
	# Scheme #
	length, results = len(columns), []
	try:
		roundCount = max(1, roundCount)
		for curveType in curveTypes:
			average = Scheme(curveType, 0)
			for round in range(1, roundCount):
				result = Scheme(curveType, round)
				for idx in range(3, 5):
					average[idx] += result[idx]
				for idx in range(6, length):
					average[idx] = -1 if -1 == average[idx] or -1 == result[idx] else average[idx] + result[idx]
			average[2] = roundCount
			for idx in range(5, length):
				average[idx] = -1 if -1 == average[idx] else average[idx] / roundCount
			results.append(average)
	except KeyboardInterrupt:
		print("\nThe experiments were interrupted by users. The program will try to save the results collected. ")
	except BaseException as e:
		print("The experiments were interrupted by the following exceptions. The program will try to save the results collected. \n\t{0}".format(e))
	
	# Output #
	print()
	if results:
		if handleFolder(os.path.split(filePath)[0]):
			flag = False # write to the file or not
			if os.path.isfile(filePath):
				try:
					flag = input("The file \"{0}\" exists. Overwrite the file or not [yN]? ".format(filePath)).upper() in ("Y", "YES", "TRUE", "1")
				except:
					print()
			else:
				flag = True
			if flag:
				try:
					df = __import__("pandas").DataFrame(results, columns = columns)
					if os.path.splitext(filePath)[1].lower() == ".csv":
						df.to_csv(filePath, index = False, float_format = "%.9f")
					else:
						df.to_excel(filePath, index = False, float_format = "%.9f")
					print("Successfully saved the results to \"{0}\" in the three-line table form. ".format(filePath))
				except:
					try:
						with open(filePath, "w", encoding = "utf-8") as f:
							f.write(str(columns) + "\n" + str(results))
						print("Successfully saved the results to \"{0}\" in the plain text form. ".format(filePath))
					except BaseException as e:
						print("Results: \n{0}\n\nFailed to save the results to \"{1}\" due to the following exception(s). \n\t{2}".format(results, filePath, e))
			else:
				print("Results: \n{0}\n\nThe overwriting is canceled by users. ".format(results))
		else:
			print("Results: \n{0}\n\nFailed to save the results to \"{1}\" since the parent folder was not created successfully. ".format(results, filePath))
	else:
		print("The results are empty. ")
	
	# End #
	iRet = EXIT_SUCCESS if results and all([all([r == roundCount for r in result[3:5]] + [r > 0 for r in result[5:length]]) for result in results]) else EXIT_FAILURE
	print("Please press the enter key to exit ({0}). ".format(iRet))
	try:
		input()
	except:
		print()
	return iRet



if "__main__" == __name__:
	exit(main())