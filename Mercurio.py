from Demetra import EpisodedTimeSeries
import pandas as pd, numpy as np, os, sys, matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error as mae

class Mercurio():
	
	eps1=5
	eps2=5
	alpha1=5
	alpha2=5
	ets = None
		
	def __init__(self):
		self.ets = EpisodedTimeSeries(self.eps1,self.eps2,self.alpha1,self.alpha2)

	def exportForSynthetic(self):
		"""
		Creates the swab2swab dataset (if not exists)
		For every battery build a folder
		In every folder there is one csv file for every espisodes
			BattertName -> 1_1.csv, 1_2.csv, .... , 4_59.csv 
		"""
		
		root4save = os.path.join(".","exportEpisodes")
		if not os.path.exists(root4save):
			os.makedirs(root4save)
			
		
		## Episode creation for real data- start
		mode = "swab2swab"
		self.ets.buildDataSet(os.path.join(".","dataset"),mode=mode,force=False) # creates dataset if does not exists
		## Episode creation for real data - end

		idxName = self.ets.dataHeader.index(self.ets.nameIndex)
		batteries = self.ets.loadDataSet()
		
		for battery in batteries:
			batteryName = self.getBatteryName(battery,idxName)
			print("Processing %s" %  batteryName)
			batteryFolder = os.path.join(root4save,batteryName)
			if not os.path.exists(batteryFolder):
				os.makedirs(batteryFolder)
			month_count = 0
			for month in battery:
				month_count += 1
				episode_count = 0
				for episode in month:
					episode_count += 1
					ep = episode[self.ets.keepY]
					fileName = "%d_%d.csv" % (month_count,episode_count)
					ep.to_csv( os.path.join(batteryFolder,fileName), index=False)
	

	def importSynthetic(self):
		
		"""
		Import the synthetic data generated from the file in csv 
		with the MatExport.py
		
		All file will be in synthetic_eps1_eps2_alpha1_alpha2_AC
		every file is a pandas dataframe zipped
		One file for battery
		"""

		root4load = os.path.join(".","synthetic_data")
		root4saveNoAC = os.path.join(".",self.ets.synthetcBlowPath)
		
		for batteryFoldeAC in os.listdir(root4load):
			
			batteryName,ac = self.getBatteryNameAndACFromFile(batteryFoldeAC);
			print("Importing synthetic data for %s @ age charge %s" % (batteryName,ac))
			saveFolder = root4saveNoAC + "_%s" % ac
			if not os.path.exists(saveFolder):
				os.makedirs(saveFolder)
			
			
			acLoadFolder = os.path.join(root4load,batteryFoldeAC)

			syntheticBatteryEpisode = []
			battery = self.ets.loadBatteryAsSingleEpisode(batteryName)
			monthCount = 0
			for month in battery:
				syntheticMonthEpisode = []
				monthCount += 1
				episodeCount = 0
				for episode in month:
					episodeCount += 1
					dfReal = episode[self.ets.syntheticImport]
					episode2load = os.path.join(acLoadFolder,"%d_%d.csv" % (monthCount,episodeCount))
					dfSynthetic = pd.read_csv(episode2load,sep=',', 
						names=([ self.ets.dataHeader[17]]),
						dtype=({ self.ets.dataHeader[17] : np.float32}))
					tempDf = dfReal.copy()
					tempDf.loc[:,self.ets.dataHeader[17]] = dfSynthetic[self.ets.dataHeader[17]].values
					
					if(False):
						self.plotSyntheticVsReale(tempDf[self.ets.dataHeader[17]].values,dfReal[self.ets.dataHeader[17]].values)
					
					
					syntheticMonthEpisode.append(tempDf)
				if(len(syntheticMonthEpisode) > 0):
					allSyntheticMonth = pd.concat(syntheticMonthEpisode)
					syntheticBatteryEpisode.append(allSyntheticMonth)
			
			syntheticSingleEpisode = pd.concat(syntheticBatteryEpisode)
			# starting from the corresponding real blow, 
			# creates the relative synthetic blows
			realBlows = self.ets.seekEpisodesBlows(battery)
			synthetic_months = []
			count = 0
			for month in realBlows:
				synthetic_blows = []
				for blow in month:
					count +=1
					hybridBlow = syntheticSingleEpisode.ix[ blow.index ]
					
					if(False and (count % 50 == 0)):
						self.plotSyntheticVsReale(hybridBlow[self.ets.dataHeader[17]].values,blow[self.ets.dataHeader[17]].values)
					
					if(hybridBlow.shape[0] != 20):
						print("Warning missing index for battery %s" % batteryName)
						#print(hybridBlow.shape)
					else:
						synthetic_blows.append(hybridBlow)
				synthetic_months.append(synthetic_blows)
			self.ets.saveZip(saveFolder,batteryName+".gz",synthetic_months)
	
	def compareSyntheticAge(self):
		root4load = os.path.join(".","synthetic_data")
		batteryName = "E464001"
		ages = [100,95,85,75,55]
		folders = []
		for age in ages:
			folderName = "%s_%d" % (batteryName,age)
			folders.append(os.path.join(root4load,folderName))
		
		count = 0
		for episode in os.listdir(folders[0]):
			count += 1
			shouldPlot = (count % 30 == 0)
			for folder in folders:
				episode2load = os.path.join(folder,episode)
				synthetic = pd.read_csv(episode2load,sep=',', 
						names=([ self.ets.dataHeader[17]]),
						dtype=({ self.ets.dataHeader[17] : np.float32}))
				if(shouldPlot):
					plt.plot(synthetic.values,label="%s_%s" % (folder,episode))
			if(shouldPlot):
				plt.grid()
				plt.legend()
				plt.show()
	
	def getBatteryName(self,battery,idxName):
		batteryName = None
		for episodeInMonth in battery:
			if(len(episodeInMonth) > 0):
				batteryName = episodeInMonth[0].values[:, idxName][0]
		return batteryName

	def getBatteryNameAndACFromFile(self,fileName):
		fileName = os.path.splitext(fileName)[0]
		batteryName = fileName.split("_")[0][1:]
		ac = fileName.split("_")[1]
		return batteryName,ac
	
	def plotSyntheticVsReale(self,synthetic,real):
		print(mae(synthetic,real))
		plt.figure()
		plt.plot(synthetic,color="navy",label="Synthetic")
		plt.plot(real,color="orange",label="Real")
		plt.grid()
		plt.legend()			
		plt.show()
		
		
	
def main():
	if(len(sys.argv) != 2):
		print("Expected one argument: import / export")
		return
	action = sys.argv[1]
	mercurio = Mercurio()
	if(action == "import"):
		print("Mercurio has come back with synthetic data!")
		mercurio.importSynthetic()
	elif(action == "export"):
		print("Mercurio is going to synthetize data!")
		mercurio.exportForSynthetic()
	elif(action == "compare"):
		mercurio.compareSyntheticAge()
	else:
		print("Mercurio does not want to perform %s!" % action)
		
main()