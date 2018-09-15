from __future__ import print_function
import tensorflow as tf
from hyperas.distributions import choice, uniform


from hyperopt import Trials, STATUS_OK, tpe, rand
from hyperas import optim
import numpy as np

	
def batchCompatible(batch_size,data):
	"""
	Transform data shape 0 in a multiple of batch_size
	"""
	exceed = data.shape[0] % batch_size
	if(exceed > 0):
		data = data[:-exceed]
	return data

def data():
	from Astrea import Astrea
	from Minerva import Minerva
	from sklearn.model_selection import train_test_split
	
	K = 5
	minerva = Minerva(eps1=5,eps2=5,alpha1=5,alpha2=5,plotMode="GUI")	
	nameIndex = minerva.ets.dataHeader.index(minerva.ets.nameIndex)
	tsIndex = minerva.ets.dataHeader.index(minerva.ets.timeIndex)
	astrea = Astrea(tsIndex,nameIndex,minerva.ets.keepY)
	
	train_ageScale = 100
	batteries = minerva.ets.loadSyntheticBlowDataSet(train_ageScale)
	
	k_idx,k_data = astrea.kfoldByKind(batteries,K)
	scaler = astrea.getScaler(k_data)
	folds4learn = []
	for i in range(len(k_data)):
		fold = k_data[i]
		foldAs3d = astrea.foldAs3DArray(fold,scaler)
		folds4learn.append(foldAs3d)
	trainIdx,testIdx = astrea.leaveOneFoldOut(K)
	
	train = None
	valid = None

	#for train_index, _ in zip(trainIdx,testIdx): 
	train_index, _ = list(zip(trainIdx,testIdx))[0]
	t = [folds4learn[train_index[i]] for i in range(1,len(train_index))]
	t = np.concatenate(t)
	v = folds4learn[train_index[0]]
	train = minerva.batchCompatible(100,t)
	valid = minerva.batchCompatible(100,v)
	#	break
	
	return train, valid, train, valid
	


	
def denseModelClassic(train, valid, agedTrain, agedValid):
	from keras.models import load_model
	from keras.callbacks import ModelCheckpoint
	from keras.models import Model
	from keras.layers import Dense, Input, Flatten, Reshape, Dropout
	from keras import optimizers
	from Minerva import huber_loss
	from Demetra import EpisodedTimeSeries

	ets = EpisodedTimeSeries(5,5,5,5)
	timesteps = 20
	inputFeatures = 2
	outputFeatures = 2
	inputs = Input(shape=(timesteps,inputFeatures),name="IN")
	
	# START HyperParameters
	dropPerc = 0.5
	codeSize = {{choice([5,7,9,12])}}
	codeMultiplier = {{choice([2,3,4])}}
	
	# END HyperParameters
	d = Dense({{choice([16,32,48,64,96,128])}},activation='relu',name="E1")(inputs)
	
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}} == 'drop':
			d = Dropout(dropPerc)(d)
		d = Dense({{choice([16,32,48,64,96,128])}},activation='relu',name="E2")(d)
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}} == 'drop':
			d = Dropout(dropPerc)(d)
		d = Dense({{choice([16,32,48,64,96,128])}},activation='relu',name="E3")(d)
	
	if {{choice(['drop', 'noDrop'])}} == 'drop':
		d = Dropout(dropPerc)(d)
	d = Dense({{choice([16,32,48,64,96,128])}},activation='relu',name="E4")(d)
	
	### s - encoding
	d = Flatten(name="F1")(d) 
	enc = Dense(codeSize,activation='relu',name="ENC")(d)
	### e - encoding
	
	
	d = Dense(codeSize*codeMultiplier,activation='relu',name="D1")(enc)
	d = Reshape((codeSize, codeMultiplier),name="R")(d)
	
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}} == 'drop':
			d = Dropout(dropPerc)(d)
		d = Dense({{choice([16,32,48,64,96,128])}},activation='relu',name="D2")(d)
	
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}} == 'drop':
			d = Dropout(dropPerc)(d)
		d = Dense({{choice([16,32,48,64,96,128])}},activation='relu',name="D3")(d)
	
	if {{choice(['drop', 'noDrop'])}} == 'drop':
		d = Dropout(dropPerc)(d)
	d = Dense({{choice([16,32,48,64,96,128])}},activation='relu',name="D4")(d)
	
	d = Flatten(name="F2")(d)
	d = Dense(outputFeatures*timesteps,activation='linear',name="DEC")(d)
	out = Reshape((timesteps, outputFeatures),name="OUT")(d)
	model = Model(inputs=inputs, outputs=out)
	
	adam = optimizers.Adam(lr=0.0005)		
	model.compile(loss=huber_loss, optimizer=adam,metrics=['mae'])
	
	#print(model.summary())
	
	path4save = "./optimizedModel.h5"
	checkpoint = ModelCheckpoint(path4save, monitor='val_loss', verbose=0,
			save_best_only=True, mode='min')
	
	model.fit(train, train,
		verbose = 0,
		batch_size=100,
		epochs=200,
		validation_data=(valid, valid)
		,callbacks=[checkpoint]
	)
	# loading the best model
	customLoss = {'huber_loss': huber_loss}
	model = load_model(path4save
			,custom_objects=customLoss)
	

	HL_aged, MAE_aged = model.evaluate(agedValid, agedValid, verbose=0)
	HL_full, MAE_full = model.evaluate(valid, valid, verbose=0)
	score = MAE_full - MAE_aged
	
	print("HL_aged: %f HL_full: %f MAE_aged: %f MAE_full: %f Score: %f" 
		% (HL_aged,HL_full, MAE_aged, MAE_full, score))
	
	
	return {'loss': HL_full, 'status': STATUS_OK, 'model': model}
	
def conv1DModelClassic(train, valid, agedTrain, agedValid):
	from keras.models import load_model
	from keras.callbacks import ModelCheckpoint
	from keras.models import Model
	from keras.layers import Dense, Input, Flatten, Reshape, Dropout
	from keras import optimizers
	from Minerva import huber_loss
	from keras.layers import Conv1D
	from Demetra import EpisodedTimeSeries
	from sklearn.metrics import mean_absolute_error
	
	inputFeatures = 2
	outputFeatures = 2
	timesteps = 20
	dropPerc = 0.5
	
	inputs = Input(shape=(timesteps,inputFeatures),name="IN")
	codeSize = {{choice([8,10,11,12])}}
	c = Conv1D({{choice([16,32,48,64,96,128,256])}}, {{choice([5,9])}},activation='relu',name="E1")(inputs)
	
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
		c = Conv1D({{choice([16,32,48,64,96,128,256])}}, {{choice([5,9])}},activation='relu',name="E2")(c)
	
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
		c = Conv1D({{choice([16,32,48,64,96,128,256])}}, {{choice([2,3])}},activation='relu',name="E3")(c)
	
	preEncodeFlat = Flatten(name="F1")(c) 
	enc = Dense(codeSize,activation='relu',name="ENC")(preEncodeFlat)
	c = Dense({{choice([16,32,48,64,96,128,256])}},activation='relu',name="D1")(enc)
	
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
		c = Dense({{choice([16,32,48,64,96,128,256])}},activation='relu',name="D2")(enc)
	
	if {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
		c = Dense({{choice([16,32,48,64,96,128,256])}},activation='relu',name="D3")(enc)
	
	c = Dense(timesteps*outputFeatures,activation='linear',name="DECODED")(c)
	out = Reshape((timesteps, outputFeatures),name="OUT")(c)
	model = Model(inputs=inputs, outputs=out)
	adam = optimizers.Adam(
		lr=0.0005
	)	
	model.compile(loss=huber_loss, optimizer=adam,metrics=['mae'])
	#print(model.summary())
	path4save = "./optimizedModel.h5"
	checkpoint = ModelCheckpoint(path4save, monitor='val_loss', verbose=0,
			save_best_only=True, mode='min')
	
	model.fit(train, train,
		verbose = 0,
		batch_size=100,
		epochs=50,
		validation_data=(valid, valid)
		,callbacks=[checkpoint]
	)
	
	customLoss = {'huber_loss': huber_loss}
	model = load_model(path4save
			,custom_objects=customLoss)
	
	
	HL_full, MAE_full = model.evaluate(valid, valid, verbose=0)
	
	ydecoded = model.predict(valid,  batch_size=100)
	maes = np.zeros(ydecoded.shape[0], dtype='float32')
	for sampleCount in range(0,ydecoded.shape[0]):
		maes[sampleCount] = mean_absolute_error(valid[sampleCount],ydecoded[sampleCount])
	
	prc = np.percentile(maes,[3,97])
	
	score = prc[1]
	
	variance = np.var(maes)
	
	print("Score: %f Variance: %f Loss: %f MAE: %f" % (score,variance,HL_full,MAE_full))
	
	return {'loss': score, 'status': STATUS_OK, 'model': model}
	
	
	
def conv2DModelClassic(train, valid, agedTrain, agedValid):
	
	from keras.models import load_model
	from keras.callbacks import ModelCheckpoint
	from keras.models import Model
	from keras.layers import Dense, Input, Flatten, Reshape, Dropout
	from keras import optimizers
	from Minerva import huber_loss
	from keras.layers import Conv2DTranspose, Conv2D
	from Demetra import EpisodedTimeSeries
	from keras.constraints import max_norm
	#from keras.backend import constant as cnt
	
	ets = EpisodedTimeSeries(5,5,5,5)
	
	inputFeatures = 2
	outputFeatures = 2
	timesteps = 20
	
	dropPerc = 0.5
	strideSize = 2
	codeSize = {{choice([4,5,6,7,8])}}

	inputs = Input(shape=(timesteps,inputFeatures),name="IN")
	c = Reshape((5,4,2),name="R2E")(inputs)
	c = Conv2D({{choice([16,32,48,64,96,128,256,512])}},strideSize,kernel_constraint=max_norm(2.),activation='relu',name="E1")(c)
	
	if  {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
		c = Conv2D({{choice([16,32,48,64,96,128,256,512])}},strideSize,kernel_constraint=max_norm(2.),activation='relu',name="E2")(c)

	if  {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}} == 'drop':
			c = Dropout(dropPerc)(c)
		c = Conv2D({{choice([16,32,48,64,96,128,256,512])}},strideSize,kernel_constraint=max_norm(2.),activation='relu',name="E3")(c)
	
	preEncodeFlat = Flatten(name="F1")(c) 
	enc = Dense(codeSize,kernel_constraint=max_norm(2.),activation='relu',name="ENC")(preEncodeFlat)
	c = Reshape((1,1,codeSize),name="R2D")(enc)

	c = Conv2DTranspose({{choice([16,32,48,64,96,128,256,512])}},strideSize,kernel_constraint=max_norm(2.),activation='relu',name="D1")(c)
	
	if  {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c) 
		c = Conv2DTranspose({{choice([16,32,48,64,96,128,256,512])}},strideSize,kernel_constraint=max_norm(2.),activation='relu',name="D2")(c)

	if  {{choice(['more', 'less'])}} == 'more':
		if {{choice(['drop', 'noDrop'])}}  == 'drop':
			c = Dropout(dropPerc)(c)
		c = Conv2DTranspose({{choice([16,32,48,64,96,128,256])}},strideSize,kernel_constraint=max_norm(2.),activation='relu',name="D3")(c)
	
	preDecFlat = Flatten(name="F2")(c) 
	c = Dense(timesteps*outputFeatures,kernel_constraint=max_norm(2.),activation='linear',name="DECODED")(preDecFlat)
	out = Reshape((timesteps, outputFeatures),name="OUT")(c)
	model = Model(inputs=inputs, outputs=out)
	adam = optimizers.Adam(
		lr=0.0005
	)	
	model.compile(loss=huber_loss, optimizer=adam,metrics=['mae'])
	#print(model.summary())
	path4save = "./optimizedModel.h5"
	checkpoint = ModelCheckpoint(path4save, monitor='val_loss', verbose=0,
			save_best_only=True, mode='min')
	
	model.fit(train, train,
		verbose = 0,
		batch_size=200,
		epochs=200,
		validation_data=(valid, valid)
		,callbacks=[checkpoint]
	)
	# loading the best model
	customLoss = {'huber_loss': huber_loss}
	model = load_model(path4save
			,custom_objects=customLoss)

	
	HL_full, MAE_full = model.evaluate(valid, valid, verbose=0)

	ydecoded = model.predict(valid,  batch_size=100)
	maes = np.zeros(ydecoded.shape[0], dtype='float32')
	for sampleCount in range(0,ydecoded.shape[0]):
		maes[sampleCount] = mean_absolute_error(valid[sampleCount],ydecoded[sampleCount])
	
	prc = np.percentile(maes,[3,97])
	sigma = np.std(maes)
	
	score = MAE_full + sigma + prc[1] #variance + MAE_full
	print("Score: %f Sigma: %f MAE: %f Loss: %f Perc: %f" % (score,sigma,MAE_full,HL_full, prc[1]))
	return {'loss': score, 'status': STATUS_OK, 'model': model}
	

	
def main():
	import time
	start = time.clock()
	best_run, best_model = optim.minimize(
										  model = conv2DModelClassic,
                                          data=data,
                                          algo=tpe.suggest,
                                          max_evals=20,
                                          trials=Trials())
	
	train, valid, agedTrain, agedValid = data()
	print("Evalutation of best performing model:")
	print(best_model.evaluate(valid, valid))
	print(best_run)
	print("Optimize - end - %f" % (time.clock() - start) )
		
main()	