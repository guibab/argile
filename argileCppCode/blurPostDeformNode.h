#ifndef __blurPostDeform_H__
#define __blurPostDeform_H__
#pragma once

// MAYA HEADER FILES:


#include <string.h>
#include <maya/MIOStream.h>
#include <maya/MStringArray.h>
#include <math.h>
#include "common.h"

#include <maya/MPxDeformerNode.h> 
#include <maya/MItGeometry.h>
#include <maya/MPxLocatorNode.h> 

#include <maya/MFnNumericAttribute.h>
#include <maya/MFnStringData.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MFnMatrixAttribute.h>
#include <maya/MFnEnumAttribute.h>
#include <maya/MFnMatrixData.h>
#include <maya/MFnUnitAttribute.h>
#include <maya/MFnCompoundAttribute.h>
#include <maya/MItMeshVertex.h>


#include <maya/MFnPointArrayData.h>
#include <maya/MFnDependencyNode.h>
#include <maya/MAnimControl.h>

#include <maya/MTime.h> 
#include <maya/MTypeId.h> 
#include <maya/MPlug.h>
#include <maya/MGlobal.h>

#include <maya/MDataBlock.h>
#include <maya/MDataHandle.h>
#include <maya/MArrayDataHandle.h>

#include <maya/MPoint.h>
#include <maya/MVector.h>
#include <maya/MMatrix.h>

#include <maya/MDagModifier.h>

#include <maya/MPxGPUDeformer.h>
#include <maya/MGPUDeformerRegistry.h>
#include <maya/MOpenCLInfo.h>
#include <maya/MViewport2Renderer.h>
#include <maya/MFnMesh.h>
#include <clew/clew_cl.h>
#include <vector>
#include <cassert>


#include <maya/MPointArray.h>
#include <maya/MFloatVectorArray.h>
#include <maya/MMatrixArray.h>
#include <maya/MFnIntArrayData.h>
#include <maya/MFnDoubleArrayData.h>

#define McheckErr(stat,msg)             \
        if ( MS::kSuccess != stat ) {   \
                cerr << msg;            \
                return MS::kFailure;    \
        }

// MAIN CLASS DECLARATION FOR THE CUSTOM NODE:
class blurSculpt : public MPxDeformerNode
{
public:
	blurSculpt();
	virtual				~blurSculpt();

	static  void*		creator();
	static  MStatus		initialize();

	// deformation function
	//
	virtual MStatus      		deform(MDataBlock& 		block,
		MItGeometry& 	iter,
		const MMatrix& 	mat,
		unsigned int		multiIndex);

	void postConstructor();

	// when the accessory is deleted, this node will clean itself up
	//
	virtual MObject&			accessoryAttribute() const;

	// create accessory nodes when the node is created
	//
	virtual MStatus				accessoryNodeSetup(MDagModifier& cmd);
	//MStatus setFrameVtx(MArrayDataHandle &deformationsHandle, MMatrix poseMat, MPoint matPoint, int deformType, int frameIndex, int theMult, float poseGainValue, float poseOffsetValue);


	void getSmoothedTangent (int indVtx,
		 MFnMesh& fnInputMesh,
		 MIntArray& smoothTangentFound,MIntArray&  tangentFound, 
		 MFloatVectorArray& tangents,  MFloatVectorArray& smoothTangents  );

	void getSmoothedNormal (int indVtx, 
                        MIntArray& smoothNormalFound,  
                        MFloatVectorArray& normals, MFloatVectorArray& smoothedNormals );
	
	/*
	MVector getTheTangent(MPointArray& deformedMeshVerticesPos,
		MArrayDataHandle& vertexTriangleIndicesData,
		MArrayDataHandle& triangleFaceValuesData,
		MArrayDataHandle& vertexVertexIndicesData,
		MArrayDataHandle& vertexFaceIndicesData,
		MFnMesh& fnInputMesh,
		MItMeshVertex& meshVertIt,
		int theVertexNumber, int deformType);
	*/
	MStatus sumDeformation (MArrayDataHandle& deformationsHandle, // the current handle of the deformation
		MFnMesh& fnInputMesh, // the current mesh
		float poseGainValue, float poseOffsetValue, float curentMult,// the pose multiplication of gain and value
		MMatrix& poseMat, MPoint& matPoint,
		bool useSmoothNormals, int deformType, 
		MIntArray& tangentFound, MIntArray&  smoothTangentFound, MIntArray&  smoothNormalFound, // if we already have the tangets or not
		MFloatVectorArray& normals, MFloatVectorArray& smoothedNormals, MFloatVectorArray& tangents, MFloatVectorArray& smoothTangents, // the values of tangents and normals
		MPointArray& theVerticesSum ); // the output array to fill

public:
	// local node attributes

	static  MObject     blurSculptMatrix; 	// blurSculpt center and axis

	static  MTypeId		id;

	static MObject inTime; // the inTime 
	static MObject uvSet; // the uv set 
	static MObject smoothNormals; // the uv set 
	/*
	static MObject vertexFaceIndices; // store the vertex face relationship
	static MObject vertexVertexIndices; // store the vertex vertex relationship

	// structure to save relationShips 
	static MObject vertexTriangleIndices; // store the vertex face relationship
	static MObject triangleFaceValues; // array of all the triangles
		static MObject vertex1; // 
		static MObject vertex2; // 
		static MObject vertex3; // 
		static MObject uValue; // 
		static MObject vValue; // 

	*/

	static MObject poses; // array of all the poses

		static MObject poseName;
		static MObject poseGain;   // mult of the pose position
		static MObject poseOffset; // add of the pose position
		static MObject poseEnabled; // boolean for enable/disable Pose
		static MObject poseMatrix; //  a matrix to calculate deformation from
		static MObject deformationType; // type of deformation (world, local, uv)

		static MObject deformations; // array of the deformations containing
			static MObject frame; // float for the frame
			static MObject frameEnabled; // float for the frame
			static MObject gain; // multier
			static MObject offset; // added
			static MObject vectorMovements; // the vectors of movements


	private : 
	// cached attributes
	int init =0;
	std::vector<MIntArray> connectedVertices;// use by MItMeshVertex getConnectedVertices
	std::vector<MIntArray> connectedFaces; // use by MItMeshVertex getConnectedFaces
	/*
	private:
	bool getConnectedVerts(MItMeshVertex& meshIter, MIntArray& connVerts, int currVertIndex);
	static MVector getCurrNormal(MPointArray& inputPts, MIntArray& connVerts);
	bool inited;
	protected:
	*/
};


// the GPU override implementation of the blurSculptNode
// 



#endif