#include "blurPostDeformNode.h"

MTypeId     blurSculpt::id(0x001226F0);
// local attributes
//
MObject		blurSculpt::blurSculptMatrix;
MObject		blurSculpt::uvSet;
MObject		blurSculpt::smoothNormals;
MObject		blurSculpt::deformationType;
MObject		blurSculpt::inTime;

MObject		blurSculpt::poses; // array of all the poses
MObject		blurSculpt::poseName;
MObject		blurSculpt::poseGain;   // mult of the pose position
MObject		blurSculpt::poseOffset; // add of the pose position
MObject		blurSculpt::poseEnabled;// boolean for enable/disable Pose
MObject		blurSculpt::poseMatrix; // a matrix to calculate deformation from
MObject		blurSculpt::deformations; // array of the deformations containing
MObject		blurSculpt::frame; // float for the frame
MObject		blurSculpt::frameEnabled;
MObject		blurSculpt::gain; // multier
MObject		blurSculpt::offset; // added
MObject		blurSculpt::vectorMovements; // the vectors of movements

blurSculpt::blurSculpt() {}
blurSculpt::~blurSculpt() {}
void* blurSculpt::creator()
{
	return new blurSculpt();

}
void blurSculpt::postConstructor()
{
	setExistWithoutInConnections(true);
}
void blurSculpt::getSmoothedNormal (int indVtx, 
                        MIntArray& smoothNormalFound,  
                        MFloatVectorArray& normals, MFloatVectorArray& smoothedNormals )
{
	MIntArray  surroundingVertices = connectedVertices[indVtx];
    int nbSurrounding = surroundingVertices.length();
    //float mult = 1. / (nbSurrounding + 1);
    MVector sumNormal = MVector(normals[indVtx]);
    for (int k = 0; k < nbSurrounding; ++k) {
      int vtxAround = surroundingVertices[k];
      sumNormal += MVector(normals[vtxAround]);
    }
    //sumNormal = .5*sumNormal + .5*normals[vtxTmp];
    sumNormal.normalize();
	smoothNormalFound[indVtx] = 1;
	smoothedNormals.set(sumNormal, indVtx);
}

void blurSculpt::getSmoothedTangent (int indVtx,MFnMesh& fnInputMesh,  MIntArray& smoothTangentFound,MIntArray&  tangentFound, MFloatVectorArray& tangents,  MFloatVectorArray& smoothTangents  ){
	// first get the tangent ------------
	if (tangentFound[indVtx] == -1) {
		tangents.set(getVertexTangentFromFace(fnInputMesh, connectedFaces[indVtx], indVtx), indVtx);
		tangentFound[indVtx] = 1;
	}
	MVector tangent = MVector(tangents[indVtx]);

	// for all connected vertices ------------
	MIntArray surroundingVertices = connectedVertices[indVtx];
	int nbSurrounding = surroundingVertices.length();
	for (int k = 0; k < nbSurrounding; ++k) {
		int vtxAround = surroundingVertices[k];
		// get its tanget ------------
		if (tangentFound[vtxAround] == -1) {
		  tangents.set(getVertexTangentFromFace(fnInputMesh, connectedFaces[vtxAround], vtxAround), vtxAround);
		  tangentFound[vtxAround] = 1;
		}
		//sum it
		tangent += tangents[vtxAround];
	}
	//normalize
	tangent.normalize();
	// set the smoothed tangent
	smoothTangentFound[indVtx] = 1;
	smoothTangents.set(tangent, indVtx);
}


MStatus blurSculpt::sumDeformation (MArrayDataHandle& deformationsHandle, // the current handle of the deformation
	MFnMesh& fnInputMesh, // the current mesh
	float poseGainValue, float poseOffsetValue, float curentMult,// the pose multiplication of gain and value
	MMatrix& poseMat, MPoint& matPoint,
	bool useSmoothNormals, int deformType, 
	MIntArray& tangentFound, MIntArray&  smoothTangentFound, MIntArray&  smoothNormalFound,// if we already have the tangets or not
	MFloatVectorArray& normals, MFloatVectorArray& smoothedNormals, MFloatVectorArray& tangents, MFloatVectorArray& smoothTangents, // the values of tangents and normals
	MPointArray& theVerticesSum ) // the output array to fill
{
	MStatus returnStatus;
	MDataHandle deformationFrameHandle = deformationsHandle.inputValue(&returnStatus);

	float gainValue = deformationFrameHandle.child(gain).asFloat();	
	float offsetValue = deformationFrameHandle.child(offset).asFloat();

	float multiplier = curentMult * (poseGainValue + poseOffsetValue)*(gainValue + offsetValue);

	MArrayDataHandle vectorMovementsHandle = deformationFrameHandle.child(vectorMovements);
	int nbVectorMvts = vectorMovementsHandle.elementCount();
	MVector tangent, normal;
	int theVertexNumber;
	MDataHandle vectorHandle;

	MMatrix mMatrix;
	MPoint zeroPt(0, 0, 0);
	MPoint theValue;
	for (int vectorIndex = 0; vectorIndex < nbVectorMvts; vectorIndex++) {
		vectorMovementsHandle.jumpToArrayElement(vectorIndex);
		theVertexNumber = vectorMovementsHandle.elementIndex();
		vectorHandle = vectorMovementsHandle.inputValue(&returnStatus);
		float3& vtxValue = vectorHandle.asFloat3();
		if (deformType == 0) {
			theValue = MPoint(multiplier*vtxValue[0], multiplier*vtxValue[1], multiplier*vtxValue[2]);
			theValue = theValue * poseMat - matPoint;
		}
		else  {  
			if (useSmoothNormals) {
				// ---- recompute normal  smoothed -----
				if (smoothNormalFound[theVertexNumber] == -1) {
					getSmoothedNormal(theVertexNumber, smoothNormalFound, normals, smoothedNormals);
				}
				normal = smoothedNormals[theVertexNumber];

				// ---- recompute tangent smoothed -----
				if (smoothTangentFound[theVertexNumber] == -1) {
					getSmoothedTangent(theVertexNumber,
						fnInputMesh,
						smoothTangentFound, tangentFound,
						tangents, smoothTangents);

				}
				tangent = smoothTangents[theVertexNumber];
			}
			else {
				// -- get the tangent -------------
				if (tangentFound[theVertexNumber] == -1) {
					tangent = getVertexTangentFromFace(fnInputMesh, connectedFaces[theVertexNumber], theVertexNumber);
					tangentFound[theVertexNumber] = 1;
					tangents.set(tangent, theVertexNumber);
				}
				tangent = tangents[theVertexNumber];
				// -- directly get the normal -------------
				normal = normals[theVertexNumber];
			}

			CreateMatrix(zeroPt, normal, tangent, mMatrix);
			theValue = MPoint(multiplier*vtxValue[0], multiplier*vtxValue[1], multiplier*vtxValue[2]) * mMatrix;
		}
		theValue += theVerticesSum[theVertexNumber];
		theVerticesSum.set(theValue, theVertexNumber);
	}
	return returnStatus;
}

/*
MVector blurSculpt::getTheTangent(MPointArray& deformedMeshVerticesPos,
	MArrayDataHandle& vertexTriangleIndicesData,
	MArrayDataHandle& triangleFaceValuesData,
	MArrayDataHandle& vertexVertexIndicesData,
	MArrayDataHandle& vertexFaceIndicesData,
	MFnMesh& fnInputMesh,
	MItMeshVertex& meshVertIt,

	int theVertexNumber, int deformType)
{
	MStatus returnStatus;
	MVector tangent;
	if (deformType==2) {//use triangle
		vertexTriangleIndicesData.jumpToArrayElement(theVertexNumber);
		MDataHandle vertTriangleHandle = vertexTriangleIndicesData.inputValue(&returnStatus);
		int triangleIndex = vertTriangleHandle.asInt();

		triangleFaceValuesData.jumpToArrayElement(triangleIndex);
		MDataHandle triangleValuesData = triangleFaceValuesData.inputValue(&returnStatus);
		int v1 = triangleValuesData.child(vertex1).asInt();
		int v2 = triangleValuesData.child(vertex2).asInt();
		int v3 = triangleValuesData.child(vertex3).asInt();
		double u = triangleValuesData.child(uValue).asDouble();
		double v = triangleValuesData.child(vValue).asDouble();

		tangent = deformedMeshVerticesPos[v3] * u + deformedMeshVerticesPos[v2] * v - deformedMeshVerticesPos[v1] * (u + v);
	}
	else if (deformType == 3) {//useVertex
		vertexVertexIndicesData.jumpToArrayElement(theVertexNumber);
		MDataHandle tangentVertexData = vertexVertexIndicesData.inputValue(&returnStatus);
		int tangentVertexIndex = tangentVertexData.asInt();
		tangent = deformedMeshVerticesPos[tangentVertexIndex] - deformedMeshVerticesPos[theVertexNumber];
	}
	else { // use maya deformType == 1
		tangent = getVertexTangent(fnInputMesh, meshVertIt, theVertexNumber);
		//OLD
		
		//vertexFaceIndicesData.jumpToArrayElement(theVertexNumber);
		//MDataHandle vertFaceHandle = vertexFaceIndicesData.inputValue(&returnStatus);
		//int faceIndex = vertFaceHandle.asInt();
		// ---- ask the value of the tangent for the wertex
		//fnInputMesh.getFaceVertexTangent(faceIndex, theVertexNumber, tangent, MSpace::kWorld);		

	}
	tangent.normalize();
	return tangent;
}
*/
MStatus blurSculpt::initialize()
{
	// local attribute initialization
	MStatus stat;
	MFnMatrixAttribute  mAttr;
	MFnStringData stringFn;
	MFnTypedAttribute tAttr;
	MFnEnumAttribute enumAttr;
	MFnUnitAttribute unitAttr;
	MFnCompoundAttribute cAttr;
	MFnNumericAttribute nAttr;

	blurSculptMatrix=mAttr.create( "locateMatrix", "lm");
	    mAttr.setStorable(false);
		mAttr.setConnectable(true);

	//  deformation attributes
	addAttribute( blurSculptMatrix);
	// the UV attribute
	MObject defaultString;
	defaultString = stringFn.create("HIII");
	uvSet = tAttr.create("uvSet", "uvs", MFnData::kString, defaultString);
	tAttr.setStorable(true);
	tAttr.setKeyable(false);
	addAttribute(uvSet);

	// the type of deformation
	deformationType = nAttr.create("deformationType", "dt", MFnNumericData::kInt, 0);
	nAttr.setStorable(true);
	nAttr.setHidden(true);

	inTime = unitAttr.create("inTime", "it", MFnUnitAttribute::kTime);
	unitAttr.setStorable(true);
	unitAttr.setKeyable(false);
	unitAttr.setWritable(true);
	unitAttr.setReadable(false);
	addAttribute(inTime);

	smoothNormals = nAttr.create("smoothNormals", "smoothNormals", MFnNumericData::kBoolean, true);
	nAttr.setKeyable(false);
	addAttribute(smoothNormals);

	/*
	// relationShip face vertex
	vertexFaceIndices = nAttr.create("vertexFaceIndices", "vertexFaceIndices", MFnNumericData::kInt, -1);
	nAttr.setArray(true);
	nAttr.setStorable(true);
	nAttr.setHidden(true);

	addAttribute(vertexFaceIndices);

	// relationShip face vertex
	vertexVertexIndices = nAttr.create("vertexVertexIndices", "vertexVertexIndices", MFnNumericData::kInt, -1);
	nAttr.setArray(true);
	nAttr.setStorable(true);
	nAttr.setHidden(true);
	addAttribute(vertexVertexIndices);

	// relationShip face vertex
	vertexTriangleIndices = nAttr.create("vertexTriangleIndices", "vertexTriangleIndices", MFnNumericData::kInt, -1);
	nAttr.setArray(true);
	nAttr.setStorable(true);
	nAttr.setHidden(true);
	addAttribute(vertexTriangleIndices);

	// relationShip triangle vertex
	vertex1 = nAttr.create("vertex1", "vertex1", MFnNumericData::kInt, -1);
	vertex2 = nAttr.create("vertex2", "vertex2", MFnNumericData::kInt, -1);
	vertex3 = nAttr.create("vertex3", "vertex3", MFnNumericData::kInt, -1);
	uValue = nAttr.create("uValue", "uValue", MFnNumericData::kDouble );
	vValue = nAttr.create("vValue", "vValue", MFnNumericData::kDouble);


	triangleFaceValues = cAttr.create("triangleFaceValues", "triangleFaceValues");
	cAttr.setArray(true);
	cAttr.setUsesArrayDataBuilder(true);
	cAttr.setStorable(true);
	cAttr.setHidden(true);
	cAttr.addChild(vertex1); cAttr.addChild(vertex2); cAttr.addChild(vertex3);
	cAttr.addChild(uValue); cAttr.addChild(vValue);	
	addAttribute(triangleFaceValues);
	*/

	// add the stored poses
	// the string for the name of the pose
	MObject poseNameS = stringFn.create("name Of pose");
	poseName = tAttr.create("poseName","poseName",MFnData::kString, poseNameS);
	tAttr.setStorable(true);		
	// the global gain of the pose 
	poseGain = nAttr.create("poseGain", "poseGain", MFnNumericData::kFloat,1.);
	// the global offset of the pose 
	poseOffset = nAttr.create("poseOffset", "poseOffset", MFnNumericData::kFloat,0.);
	poseEnabled = nAttr.create("poseEnabled", "poseEnabled", MFnNumericData::kBoolean, true);
	nAttr.setKeyable(false);
	// matrix to calculate deformation from
	poseMatrix = mAttr.create("poseMatrix", "poseMatrix");
	mAttr.setStorable(false);
	mAttr.setConnectable(true);

	// the frame for the pose
	frame = nAttr.create("frame", "frame", MFnNumericData::kFloat);
	// the gain of the deformation
	frameEnabled = nAttr.create("frameEnabled", "frameEnabled", MFnNumericData::kBoolean, true);
	nAttr.setKeyable(false);

	gain = nAttr.create("gain", "gain", MFnNumericData::kFloat,1.0);
	// the offset of the deformation
	offset = nAttr.create("offset", "offset", MFnNumericData::kFloat,0.);
	// the vectorMovement of the vertices	
	vectorMovements = nAttr.create("vectorMovements", "vectorMovements", MFnNumericData::k3Float);
	nAttr.setArray(true);

	// create the compound object
	deformations = cAttr.create("deformations", "deformations");
	cAttr.setArray(true);
	cAttr.setUsesArrayDataBuilder(true);
	cAttr.setStorable(true);
	cAttr.setHidden(true);
	cAttr.addChild(frame);
	cAttr.addChild(frameEnabled);
	cAttr.addChild(gain);
	cAttr.addChild(offset);
	cAttr.addChild(vectorMovements);

	// create the compound object
	poses = cAttr.create("poses", "poses");
	cAttr.setArray(true);
	cAttr.setUsesArrayDataBuilder(true);
	cAttr.setStorable(true);
	cAttr.setHidden(true);
	cAttr.addChild(poseName);
	cAttr.addChild(poseGain);
	cAttr.addChild(poseOffset);
	cAttr.addChild(poseEnabled);
	cAttr.addChild(poseMatrix);
	cAttr.addChild(deformationType);

	cAttr.addChild(deformations);
	addAttribute(poses);
	// now the attribute affects

	attributeAffects( blurSculpt::blurSculptMatrix, blurSculpt::outputGeom );
	//attributeAffects(blurSculpt::uvSet, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::inTime, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::deformationType, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::vectorMovements, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::poseOffset, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::poseGain, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::poseEnabled, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::poseMatrix, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::frame, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::frameEnabled, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::offset, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::gain, blurSculpt::outputGeom);
	attributeAffects(blurSculpt::smoothNormals, blurSculpt::outputGeom);
	
	return MStatus::kSuccess;
}




MStatus
blurSculpt::deform( MDataBlock& block,
				MItGeometry& iter,
				const MMatrix& /*m*/,
				unsigned int multiIndex)
//
// Method: deform
//
// Description:   Deform the point with a squash algorithm
//
// Arguments:
//   block		: the datablock of the node
//	 iter		: an iterator for the geometry to be deformed
//   m    		: matrix to transform the point into world space
//	 multiIndex : the index of the geometry that we are deforming
{
	MStatus returnStatus;

	MArrayDataHandle hInput = block.outputArrayValue(input, &returnStatus);
	if (MS::kSuccess != returnStatus) return returnStatus;
	returnStatus = hInput.jumpToElement(multiIndex);
	if (MS::kSuccess != returnStatus) return returnStatus;

	MObject oInputGeom = hInput.outputValue().child(inputGeom).asMesh();
	MFnMesh fnInputMesh(oInputGeom, &returnStatus);
	if (MS::kSuccess != returnStatus) return returnStatus;

	// get the mesh before deformation, not after, or Idk 
	/*
	MObject thisNode = this->thisMObject();
	MPlug inPlug(thisNode, input);
	inPlug.selectAncestorLogicalIndex(multiIndex, input);
	MDataHandle hInput = block.inputValue(inPlug);

	MDataHandle inputGeomDataH = hInput.inputValue().child(inputGeom);
	MDataHandle hOutput = block.outputValue(plug);
	hOutput.copy(inputGeomDataH);

	MFnMesh inputMesh(inputGeomDataH.asMesh());
	*/

	// Envelope data from the base class.
	// The envelope is simply a scale factor.
	//
	MDataHandle envData = block.inputValue(envelope, &returnStatus);
	if (MS::kSuccess != returnStatus) return returnStatus;
	float env = envData.asFloat();	

	// Get the matrix which is used to define the direction and scale
	// of the blurSculpt.
	//
	MDataHandle matData = block.inputValue(blurSculptMatrix, &returnStatus );
	if (MS::kSuccess != returnStatus) return returnStatus;
	MMatrix omat = matData.asMatrix();
	MMatrix omatinv = omat.inverse();
	
	MDataHandle timeData = block.inputValue(inTime, &returnStatus);
	if (MS::kSuccess != returnStatus) return returnStatus;
	MTime theTime = timeData.asTime();
	double theTime_value = theTime.value();
	
	/*
	// relationShip vtx face
	MArrayDataHandle vertexFaceIndicesData = block.inputValue(vertexFaceIndices, &returnStatus);
	if (MS::kSuccess != returnStatus) return returnStatus;	
	// relationShip vtx vtx
	MArrayDataHandle vertexVertexIndicesData = block.inputValue(vertexVertexIndices, &returnStatus);
	if (MS::kSuccess != returnStatus) return returnStatus;
	// triangle vtx f
	MArrayDataHandle vertexTriangleIndicesData = block.inputValue(vertexTriangleIndices, &returnStatus);
	if (MS::kSuccess != returnStatus) return returnStatus;
	// triangle data
	MArrayDataHandle triangleFaceValuesData = block.inputValue(triangleFaceValues, &returnStatus);
	if (MS::kSuccess != returnStatus) return returnStatus;
	*/


	/*
	MTime currentFrame = MAnimControl::currentTime();
	float theTime_value = float(currentFrame.value());
	*/
	//cout << "time is  " << theTime_value << endl;
	//MGlobal::displayInfo(MString("time is : ") + theTime_value);

	// READ IN ".uvSet" DATA:
	MDataHandle uvSetDataHandle = block.inputValue(uvSet);
	MString theUVSet = uvSetDataHandle.asString();
	bool isUvSet(false);
	/*
	MStringArray setNames;
	meshFn.getUVSetNames(setNames);
	MString stringToPrint("US sets :");
	unsigned nbUvSets = setNames.length();
	for (unsigned i = 0; i < nbUvSets; i++) {
		stringToPrint += " " + setNames[i];
		isUvSet |= theUVSet == setNames[i];
	}
	MString currentUvSet = meshFn.currentUVSetName(&status);
	if (!isUvSet)
		theUVSet = currentUvSet;
	MGlobal::displayInfo(currentUvSet );
	MGlobal::displayInfo(stringToPrint);
	MGlobal::displayInfo(MString("uvSet to Use is : ") + theUVSet );
	if (isUvSet )
	MGlobal::displayInfo(MString("Found") );

	*/
	int nbVertices = fnInputMesh.numVertices();
	MPointArray theVerticesSum(nbVertices);
	
	// iterate through each point in the geometry
	MArrayDataHandle posesHandle = block.inputValue(poses, &returnStatus);
	unsigned int nbPoses = posesHandle.elementCount();
	unsigned int nbDeformations;
	MDataHandle poseInputVal, poseNameHandle, poseGainHandle, poseOffsetHandle, poseEnabledHandle;
	MDataHandle deformationTypeData;
	//int deformType;
	//MDataHandle deformationFrameHandle, frameEnabledHandle , frameHandle, gainHandle, offsetHandle, vectorHandle ;
	MString thePoseName;
	//float theFrame, poseGainValue, poseOffsetValue, gainValue, offsetValue;
	//int theVertexNumber;

	//loop for each output conneted curves
	//MItMeshVertex vertexIter(oInputGeom);	
	//MDataHandle vertFaceHandle, vertTriangleHandle, triangleValuesData, tangentVertexData;	
	//int faceIndex, triangleIndex, tangentVertexIndex;


	// ---  get all normals at once ------------------------
	MFloatVectorArray normals;
	fnInputMesh.getVertexNormals(false, normals, MSpace::kWorld);
	// ---  this data is to be build ------------------------
	MFloatVectorArray tangents(nbVertices), smoothTangents(nbVertices);	
	MFloatVectorArray triangleTangents(nbVertices);
	MPointArray deformedMeshVerticesPos;
	fnInputMesh.getPoints(deformedMeshVerticesPos, MSpace::kObject);
	
	MIntArray tangentFound(nbVertices, -1); // init at -1
	MIntArray smoothTangentFound(nbVertices, -1); // init at -1	
	MIntArray smoothNormalFound(nbVertices, -1); // init at -1	
	// -------------------- smooth the normals -----------------------------------------------
	//MIntArray surroundingVertices;
	MFloatVectorArray smoothedNormals(nbVertices);
	MDataHandle smoothNormalsData = block.inputValue(smoothNormals, &returnStatus);
	bool useSmoothNormals = smoothNormalsData.asBool();

	// if init is false means is a new deformed or a recent opend scene, so create cache form scratch
	if (!init){
		MItMeshVertex vertexIter(oInputGeom);
		connectedVertices.resize(nbVertices);
		connectedFaces.resize(nbVertices);
		for (int vtxTmp = 0; !vertexIter.isDone(); vertexIter.next(), ++vtxTmp) {
			MIntArray surroundingVertices, surroundingFaces;
			vertexIter.getConnectedVertices(surroundingVertices);
			connectedVertices[vtxTmp] = surroundingVertices;

			vertexIter.getConnectedFaces(surroundingFaces);
			connectedFaces[vtxTmp] = surroundingFaces;
		}
		init=1;
	}

	// -------------------- end compute smoothed normals -------------------------------
	int prevFrameIndex = 0, nextFrameIndex = 0;
	float prevFrame = 0, nextFrame = 0;
	bool hasPrevFrame = false, hasNextFrame = false;
	float prevMult = 0., nextMult = 0., multiplier=0.;
	int deformType;
	float poseGainValue, poseOffsetValue, theFrame;
	MDataHandle deformationFrameHandle, frameEnabledHandle, frameHandle;
	//MGlobal::displayInfo(MString("useTriangle : ") + useTriangle + MString(" useVertex : ") + useVertex);
	for (unsigned int poseIndex = 0; poseIndex < nbPoses; poseIndex++) {
		//MPlug posePlug = allPosesPlug.elementByLogicalIndex(poseIndex);
		//posesHandle.jumpToArrayElement(poseIndex);

		// use this method for arrays that are sparse
		poseInputVal = posesHandle.inputValue(&returnStatus);
		poseEnabledHandle = poseInputVal.child(poseEnabled);
		bool isPoseEnabled = poseEnabledHandle.asBool();
		if (isPoseEnabled) {
			deformationTypeData = poseInputVal.child(deformationType);
			deformType = deformationTypeData.asInt();

			//poseNameHandle  = poseInputVal.child(poseName);
			//thePoseName = poseNameHandle.asString();
			//MGlobal::displayInfo(MString("poseName : ") + thePoseName);
			poseGainHandle = poseInputVal.child(poseGain);
			poseGainValue = poseGainHandle.asFloat();

			poseOffsetHandle = poseInputVal.child(poseOffset);
			poseOffsetValue = poseOffsetHandle.asFloat();

			MArrayDataHandle deformationsHandle = poseInputVal.child(deformations);
			nbDeformations = deformationsHandle.elementCount();
			prevFrameIndex = 0; nextFrameIndex = 0;
			prevFrame = 0; nextFrame = 0;
			hasPrevFrame = false; hasNextFrame = false;
			// check the frames in between
			for (unsigned int deformIndex = 0; deformIndex < nbDeformations; deformIndex++) {
				//deformationsHandle.jumpToArrayElement(deformIndex);
				deformationFrameHandle = deformationsHandle.inputValue(&returnStatus);

				frameEnabledHandle = deformationFrameHandle.child(frameEnabled);
				bool isFrameEnabled = frameEnabledHandle.asBool();
				if (isFrameEnabled) {
					frameHandle = deformationFrameHandle.child(frame);
					theFrame = frameHandle.asFloat();
					if (theFrame < theTime_value) {
						if ((!hasPrevFrame) || (theFrame > prevFrame)) {
							hasPrevFrame = true;
							prevFrameIndex = deformIndex;
							prevFrame = theFrame;
						}
					}
					else if (theFrame > theTime_value) {
						if ((!hasNextFrame) || (theFrame < nextFrame)) {
							hasNextFrame = true;
							nextFrameIndex = deformIndex;
							nextFrame = theFrame;
						}
					}
					else if (theFrame == theTime_value) { // equality
						hasPrevFrame = true;
						hasNextFrame = false;
						prevFrameIndex = deformIndex;
						prevFrame = theFrame;
						break;
					}
				}
				deformationsHandle.next();
			}
			// get the frames multiplication
			prevMult = 0.; nextMult = 0.;
			if (hasPrevFrame) prevMult = 1.;
			if (hasNextFrame) nextMult = 1.;
			if (hasPrevFrame && hasNextFrame) {
				nextMult = float(theTime_value - prevFrame) / float(nextFrame - prevFrame);
				prevMult = float(1. - nextMult);
			}
			MDataHandle poseMatrixData = poseInputVal.child(poseMatrix);
			MMatrix poseMat = poseMatrixData.asMatrix();
			MPoint matPoint = MPoint(0, 0, 0)*poseMat;
			if (hasPrevFrame) {
				deformationsHandle.jumpToArrayElement(prevFrameIndex);

				sumDeformation (deformationsHandle, // the current handle of the deformation
				fnInputMesh,
				poseGainValue, poseOffsetValue, prevMult,// the pose multiplication of gain and value
				poseMat, matPoint, 
				useSmoothNormals,deformType, 
				tangentFound, smoothTangentFound, smoothNormalFound, // if we already have the tangets or not
				normals, smoothedNormals, tangents, smoothTangents, // the values of tangents and normals
				//perFaceConnectedVertices, // the connected vertices already stored   //   to remove !!!
				theVerticesSum ); // the output array to fill

			}
			if (hasNextFrame) {
				deformationsHandle.jumpToArrayElement(nextFrameIndex);

				sumDeformation (deformationsHandle, // the current handle of the deformation
				fnInputMesh,
				poseGainValue, poseOffsetValue, nextMult, // the pose multiplication of gain and value
				poseMat, matPoint,
				useSmoothNormals,deformType, 
				tangentFound, smoothTangentFound, smoothNormalFound, // if we already have the tangets or not
				normals, smoothedNormals, tangents, smoothTangents, // the values of tangents and normals
				//perFaceConnectedVertices, // the connected vertices already stored   //   to remove !!!
				theVerticesSum ); // the output array to fill
			}
		}
		posesHandle.next();
	}
	MPoint pt, resPos, toset;
	float weight;
	for ( ; !iter.isDone(); iter.next()) {		
		int theindex = iter.index();
		pt = iter.position();
		//pt *= omatinv;		
		weight = weightValue(block,multiIndex, theindex);
		resPos = (pt + theVerticesSum[theindex]) * omat;
		toset = double(env*weight) * resPos + double(1. - env*weight) * pt;
		iter.setPosition(toset);
	}
	return returnStatus;
}

/* override */
MObject&
blurSculpt::accessoryAttribute() const
//
//	Description:
//	  This method returns a the attribute to which an accessory	
//    shape is connected. If the accessory shape is deleted, the deformer
//	  node will automatically be deleted.
//
//    This method is optional.
//
{
	return blurSculpt::blurSculptMatrix;
}

/* override */
MStatus
blurSculpt::accessoryNodeSetup(MDagModifier& cmd)
//
//	Description:
//		This method is called when the deformer is created by the
//		"deformer" command. You can add to the cmds in the MDagModifier
//		cmd in order to hook up any additional nodes that your node needs
//		to operate.
//
//		In this example, we create a locator and attach its matrix attribute
//		to the matrix input on the blurSculpt node. The locator is used to
//		set the direction and scale of the random field.
//
//	Description:
//		This method is optional.
//
{
	MStatus result;

	// hook up the accessory node
	//
	/*
	MObject objLoc = cmd.createNode(MString("locator"),
									MObject::kNullObj,
									&result);

		
	MFnDependencyNode fnLoc(objLoc);
	MString attrName;
	attrName.set("matrix");
	MObject attrMat = fnLoc.attribute(attrName);
	result = cmd.connect(objLoc, attrMat, this->thisMObject(), blurSculpt::blurSculptMatrix);
		
	*/
	//- Connect time1 node with time of node
	MSelectionList selList;

	MObject timeNode;
	MGlobal::getSelectionListByName(MString("time1"), selList);
	selList.getDependNode(0, timeNode);
	selList.clear();

	MFnDependencyNode fnTimeNode(timeNode);
	MObject timeAttr = fnTimeNode.attribute(MString("outTime"), &result);		
	cmd.connect(timeNode, timeAttr, this->thisMObject(), blurSculpt::inTime);
		
	return result;
}

