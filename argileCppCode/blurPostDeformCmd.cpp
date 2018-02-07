#include "blurPostDeformCmd.h"
#include "blurPostDeformNode.h"

#include <maya/MArgDatabase.h>
#include <maya/MFnDoubleArrayData.h>
#include <maya/MFnIntArrayData.h>
#include <maya/MFnMatrixData.h>
#include <maya/MFnMesh.h>
#include <maya/MGlobal.h>
#include <maya/MItDependencyGraph.h>
#include <maya/MItGeometry.h>
#include <maya/MItSelectionList.h>
#include <maya/MMeshIntersector.h>
#include <maya/MFnSingleIndexedComponent.h>
#include <maya/MFnWeightGeometryFilter.h>
#include <maya/MSyntax.h>
#include <algorithm>
#include <cassert>
#include <utility>

#define PROGRESS_STEP 100
#define TASK_COUNT 32

/**
  A version number used to support future updates to the binary wrap binding file.
*/
const float kWrapFileVersion = 1.0f;

const char* blurSculptCmd::kName = "blurSculpt";
const char* blurSculptCmd::kQueryFlagShort = "-q";
const char* blurSculptCmd::kQueryFlagLong = "-query";
const char* blurSculptCmd::kNameFlagShort = "-n";
const char* blurSculptCmd::kNameFlagLong = "-name";
const char* blurSculptCmd::kAddPoseNameFlagShort = "-ap";
const char* blurSculptCmd::kAddPoseNameFlagLong = "-addPose";
const char* blurSculptCmd::kPoseNameFlagShort = "-pn";
const char* blurSculptCmd::kPoseNameFlagLong = "-poseName";
const char* blurSculptCmd::kPoseTransformFlagShort = "-pt";
const char* blurSculptCmd::kPoseTransformFlagLong = "-poseTransform";
const char* blurSculptCmd::kListPosesFlagShort = "-lp";
const char* blurSculptCmd::kListPosesFlagLong = "-listPoses";
const char* blurSculptCmd::kListFramesFlagShort = "-lf";
const char* blurSculptCmd::kListFramesFlagLong = "-listFrames";
const char* blurSculptCmd::kAddFlagShort = "-add";
const char* blurSculptCmd::kAddFlagLong = "-addAtTime";
const char* blurSculptCmd::kOffsetFlagShort = "-of";
const char* blurSculptCmd::kOffsetFlagLong = "-offset";
const char* blurSculptCmd::kRemoveTimeFlagShort = "-rmv";
const char* blurSculptCmd::kRemoveTimeFlagLong = "-removeAtTime";
const char* blurSculptCmd::kHelpFlagShort = "-h";
const char* blurSculptCmd::kHelpFlagLong = "-help";

/**
  Displays command instructions.
*/
void DisplayHelp() {
  MString help;
  help += "Flags:\n"; 
  help += "-name (-n):            String     Name of the blurSclupt node to create.\n"; 
  help += "-query (-q):           N/A        Query mode.\n";
  help += "-listPoses (-lp):      N/A        In query mode return the list of poses stored\n";
  help += "-listFrames (-lf):     N/A		 combine with poseName and query mode\n";
  help += "                                  return the list of frame used\n";
  help += "-addPose (-ap):        N/A        Add a pose, use with poseName \n";
  help += "-poseName (-pn):       String     the name of the pose we want to add or edit\n";
  help += "-poseTransform (-pt):  String     the transform node for the pose to add\n";
  help += "-addAtTime (-nbm)      String     the mesh target to add at the currentTime\n";
  help += "                                  needs pose name\n";
  help += "-offset (-of)          Float      the offset distance to see if a vertex is moved\n";
  help += "                                  default 0.001 | used in addAtTime\n";
  help += "-removeAtTime (-rmv):  N/A        Remove this pose at this time\n";
  help += "-help (-h)             N/A        Display this text.\n";
  MGlobal::displayInfo(help);
}

blurSculptCmd::blurSculptCmd()
    : 
      name_("blurSculpt#"),
      command_(kCommandCreate),
	  getListPoses_(false),
	  getListFrames_(false),
	  connectTransform_(false),
	  aOffset_ (0.001), 
	  aPoseGain_ (1),
	  aPoseOffset_(0)
{
}

MSyntax blurSculptCmd::newSyntax() {
  MSyntax syntax;
  syntax.addFlag(kQueryFlagShort, kQueryFlagLong);
  syntax.addFlag(kListPosesFlagShort, kListPosesFlagLong);
  syntax.addFlag(kListFramesFlagShort, kListFramesFlagLong);
  syntax.addFlag(kNameFlagShort, kNameFlagLong, MSyntax::kString);
  syntax.addFlag(kAddPoseNameFlagShort, kAddPoseNameFlagLong);
  syntax.addFlag(kPoseNameFlagShort, kPoseNameFlagLong, MSyntax::kString);
  syntax.addFlag(kPoseTransformFlagShort, kPoseTransformFlagLong, MSyntax::kString);
  syntax.addFlag(kAddFlagShort, kAddFlagLong, MSyntax::kString);
  syntax.addFlag(kOffsetFlagShort, kOffsetFlagLong, MSyntax::kDouble);  
  syntax.addFlag(kRemoveTimeFlagShort, kRemoveTimeFlagLong);
  syntax.addFlag(kHelpFlagShort, kHelpFlagLong);
  syntax.setObjectType(MSyntax::kSelectionList, 0, 255);
  syntax.useSelectionAsDefault(true);
  return syntax;
}

void* blurSculptCmd::creator() {                                
  return new blurSculptCmd;                    
}    

bool blurSculptCmd::isUndoable() const {
  return command_ == kCommandCreate;  // Only creation will be undoable
}

MStatus blurSculptCmd::doIt(const MArgList& args) {
	MStatus status;

	status = GatherCommandArguments(args);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	status = GetGeometryPaths();
	CHECK_MSTATUS_AND_RETURN_IT(status);
	if (command_ == kCommandHelp) { return MS::kSuccess; }
	if (command_ == kCommandAddPoseAtTime) {
		//MGlobal::displayInfo(MString("command is : [kCommandAddPoseAtTime]"));
		status = GetLatestBlurSculptNode();
	}
	if (command_ == kCommandAddPose) {
		//MGlobal::displayInfo(MString("command is : [kCommandAddPose]"));
		addAPose();
		return MS::kSuccess;
	}
	MFnDagNode fnMeshDriven(meshDeformed_);

	if (command_ == kCommandCreate) {	
		//MGlobal::displayInfo(MString("command is : [kCommandCreate]"));

		// Add the blurSculpt creation command to the modifier.
		MString command = "deformer -type blurSculpt -n \"" + name_ + "\"";
		command += " " + fnMeshDriven.partialPathName();
		//MGlobal::displayInfo(MString("command is : [") + command + MString("]"));

		status = dgMod_.commandToExecute(command);
		status = dgMod_.doIt();
		status = GetLatestBlurSculptNode();
		//setFaceVertexRelationShip();
		//computeBarycenters();

		MFnDependencyNode fnBlurSculptNode(oBlurSculptNode_);
		setResult (fnBlurSculptNode.name());
	}
	CHECK_MSTATUS_AND_RETURN_IT(status);
	status = getListPoses();
	CHECK_MSTATUS_AND_RETURN_IT(status);
	if (command_ == kCommandAddPoseAtTime) {
		status = GetLatestBlurSculptNode();
		MFnDependencyNode fnBlurSculptNode(oBlurSculptNode_);

		//MGlobal::displayInfo(MString("Adding : [") + targetMeshAdd_ + MString("] to mesh [")+ fnMeshDriven.partialPathName() + MString("]"));
		//MGlobal::displayInfo(MString("       fnBlurSculptNode : [") + fnBlurSculptNode.name() + MString("]"));
		addAFrame();
	}
	else if (command_ == kCommandQuery) {
		//MGlobal::displayInfo(MString("Query : getListPoses_  [") + getListPoses_ + MString("] "));
		//MGlobal::displayInfo(MString("        getListFrames_  [") + getListFrames_ + MString("] ") );
		//MGlobal::displayInfo(MString("        poseName_  [") + poseName_ + MString("] "));
		int nb = allPosesNames_.length();
		if (getListPoses_) 
		{
			MString toDisplay("the poses names : ");
			MString tst("test");
			
			for (int i = 0; i < nb; i++) {
				toDisplay += MString("[") + allPosesNames_[i] + MString("]");
				//appendToResult(static_cast<int>(1));
				appendToResult(allPosesNames_[i].asChar () );
			}
			//MGlobal::displayInfo(toDisplay);
		}
		if (getListFrames_) {
			int poseIndex = getMStringIndex(allPosesNames_, poseName_); //allPosesNames_.indexOf(poseName_);
			if (poseIndex == -1) {
				MGlobal::displayError(poseName_+" is not a pose");
				return MS::kFailure;
			}
			else {
				getListFrames(poseIndex);
				MString toDisplay("the frame for pose "+ poseName_ +" are : \n");
				for (unsigned int i = 0; i < allFramesFloats_.length(); i++) {
					toDisplay += MString(" [") + allFramesFloats_[i] + MString("]");
					appendToResult(static_cast<float>(allFramesFloats_[i]));
				}
				//MGlobal::displayInfo(toDisplay);
			}
		}
		//cout << "Normal: "  << endl;
	}
	return MS::kSuccess;
}

MStatus blurSculptCmd::GatherCommandArguments(const MArgList& args) {
  MStatus status;
  MArgDatabase argData(syntax(), args);
  argData.getObjects(selectionList_);
  if (argData.isFlagSet(kHelpFlagShort)) {
    command_ = kCommandHelp;
    DisplayHelp();
    return MS::kSuccess;
  }
  if (argData.isFlagSet(kNameFlagShort)) {
    name_ = argData.flagArgumentString(kNameFlagShort, 0, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
  }
  if (argData.isFlagSet(kPoseNameFlagShort)) {
    poseName_ = argData.flagArgumentString(kPoseNameFlagShort, 0, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
  }
  if (argData.isFlagSet(kQueryFlagShort)) {
	  command_ = kCommandQuery;
  }
  if (argData.isFlagSet(kListPosesFlagShort)) {
	  getListPoses_ = true;
  }
  if (argData.isFlagSet(kListFramesFlagShort)) {
	  getListFrames_ = true;
  }
  if (command_ == kCommandQuery) return MS::kSuccess;
  
  if (argData.isFlagSet(kPoseTransformFlagShort)) {
	  poseTransformStr_ = argData.flagArgumentString(kPoseTransformFlagShort, 0, &status);
	  MSelectionList selListA;
	  MGlobal::getSelectionListByName(poseTransformStr_, selListA);
	  selListA.getDependNode(0, poseTransform_);
	  //selList.getDagPath(0, poseTransform_);
	  selListA.clear();
	  connectTransform_ = true;
  }

  if (argData.isFlagSet(kOffsetFlagShort)) {
	  MString OffsetStr = argData.flagArgumentString(kOffsetFlagShort, 0, &status);
	  aOffset_ = OffsetStr.asFloat();
  }
 
  if (argData.isFlagSet(kAddPoseNameFlagShort)) {
	  command_ = kCommandAddPose;
	  return MS::kSuccess;
  }
  if (argData.isFlagSet(kAddFlagShort)) {
	  targetMeshAdd_ = argData.flagArgumentString(kAddFlagShort, 0, &status);
	  MSelectionList selList;
	  MGlobal::getSelectionListByName(targetMeshAdd_, selList);
	  selList.getDagPath(0, meshTarget_);
	  selList.clear();
	  status = GetShapeNode(meshTarget_);

	  command_ = kCommandAddPoseAtTime;
	  CHECK_MSTATUS_AND_RETURN_IT(status);
  }
  else {
	  command_ = kCommandCreate;
  }
  return MS::kSuccess;
}

MStatus blurSculptCmd::GetGeometryPaths() {
  MStatus status;
  if (selectionList_.length() == 0 ) {
	  MGlobal::displayError("select at least a mesh");
	  return MS::kFailure;
  }
  if (command_ == kCommandQuery || command_ == kCommandHelp || command_ == kCommandAddPose)
  {	  
	  MObject inputNode ;
	  status = selectionList_.getDependNode(0, inputNode);
	  CHECK_MSTATUS_AND_RETURN_IT(status);
	  //MGlobal::displayInfo("query get node");
	  MFnDependencyNode inputNodeDep(inputNode, &status);
	  if (inputNodeDep.typeId() == blurSculpt::id) {
		  oBlurSculptNode_ = inputNode;
		  //MGlobal::displayInfo("query we have the blurSculpt");
		  return MS::kSuccess;		  
	  }
  }
  else {
	  // The driver is selected last
	  status = selectionList_.getDagPath(0, meshDeformed_);
	  CHECK_MSTATUS_AND_RETURN_IT(status);
	  status = GetShapeNode(meshDeformed_);
	  // The driver must be a mesh for this specific algorithm.
	  if (command_ == kCommandCreate && !meshDeformed_.hasFn(MFn::kMesh)) {
		  MGlobal::displayError("blurSculpt works only on  mesh.");
		  return MS::kFailure;
	  }
  }
  /*
  meshDeformed_

  if (command_ != kCommandCreate && meshDeformed_.(blurSculpt::id)) {

  }
  */
  return MS::kSuccess;
}
/*
MStatus blurSculptCmd::setFaceVertexRelationShip() {
	MStatus status;
	MFnMesh fnDeformedMesh(meshDeformed_, &status);
	int nbDeformedVtx = fnDeformedMesh.numVertices();
	MItMeshVertex vertexIter(meshDeformed_);

	MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);
	MPlug vertexFaceIndicesPlug = blurSculptDepNode.findPlug(blurSculpt::vertexFaceIndices);
	MPlug vertexVertexIndicesPlug = blurSculptDepNode.findPlug(blurSculpt::vertexVertexIndices);

	MIntArray faces, edges, vertexList;
	MPlug theVertexFace, theVertextVertex;
	
	int vertexInd = 0;
	for (; !vertexIter.isDone(); vertexIter.next()) {
		vertexIter.getConnectedFaces(faces);
		int faceIndex = faces[0];
		vertexIter.getConnectedEdges(edges);
		int2 vertexList;
		int nextVertex;
		fnDeformedMesh.getEdgeVertices(edges[0], vertexList);
		if (vertexList[0] == vertexInd) 
			nextVertex = vertexList[1];
		else
			nextVertex = vertexList[0];

		theVertexFace = vertexFaceIndicesPlug.elementByLogicalIndex(vertexInd, &status);
		theVertexFace.setValue(faceIndex);

		theVertextVertex = vertexVertexIndicesPlug.elementByLogicalIndex(vertexInd, &status);
		theVertextVertex.setValue(nextVertex);

		vertexInd++;
	}
	return MS::kSuccess;

}
*/
MStatus blurSculptCmd::GetLatestBlurSculptNode() {
	MStatus status;
	MObject oDriven = meshDeformed_.node();

	// Since we use MDGModifier to execute the deformer command, we can't get
	// the created deformer node, so we need to find it in the deformation chain.
	MItDependencyGraph itDG(oDriven,
		MFn::kGeometryFilt,
		MItDependencyGraph::kUpstream,
		MItDependencyGraph::kDepthFirst,
		MItDependencyGraph::kNodeLevel,
		&status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	MObject oDeformerNode;
	for (; !itDG.isDone(); itDG.next()) {
		oDeformerNode = itDG.currentItem();
		MFnDependencyNode fnNode(oDeformerNode, &status);
		CHECK_MSTATUS_AND_RETURN_IT(status);
		if (fnNode.typeId() == blurSculpt::id) {
			oBlurSculptNode_ = oDeformerNode;
			return MS::kSuccess;
		}
	}
	return MS::kFailure;
}

MStatus blurSculptCmd::GetPreDeformedMesh(MObject& blurSculptNode, MDagPath& pathMesh) {
	MStatus status;
	/*
	// Get the bind mesh connected to the message attribute of the wrap deformer
	MPlug plugBindMesh(oWrapNode, blurSculpt::aBindDriverGeo);
	MPlugArray plugs;
	plugBindMesh.connectedTo(plugs, true, false, &status);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	if (plugs.length() == 0) {
		MGlobal::displayError("Unable to rebind.  No bind mesh is connected.");
		return MS::kFailure;
	}
	MObject oBindMesh = plugs[0].node();
	status = MDagPath::getAPathTo(oBindMesh, pathBindMesh);
	CHECK_MSTATUS_AND_RETURN_IT(status);
	*/
	return MS::kSuccess;
}

MStatus blurSculptCmd::getListPoses() {
	MStatus status;
	allPosesNames_.clear();
	allPosesIndices_.clear();

	MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);
	// get list of poses
	MPlug posesPlug = blurSculptDepNode.findPlug(blurSculpt::poses, &status);
	unsigned int nbPoses = posesPlug.numElements(&status);

	//MIntArray iarrIndexes;	// array to hold each valid index number.
	unsigned nEle = posesPlug.getExistingArrayAttributeIndices(allPosesIndices_, &status);
	
	//for (unsigned int element = 0; element < iarrIndexes.length(); element++)
	for (unsigned int element = 0; element < nbPoses; element++)
	{
		// do not use elementByLogicalIndex
		MPlug thePosePlug = posesPlug.elementByPhysicalIndex(element, &status);
		MPlug thePoseNamePlug = thePosePlug.child(blurSculpt::poseName);
		allPosesNames_.append(thePoseNamePlug.asString());
		//unsigned int logicalIndex = newTargetPlug.logicalIndex(&stat);		
	}
	return MS::kSuccess;
}

MStatus blurSculptCmd::getListFrames( int poseIndex) {
	//MGlobal::displayInfo(MString("\n query list Poses: \n") );

	MStatus status;
	allFramesFloats_.clear();

	MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);
	MPlug posesPlug = blurSculptDepNode.findPlug(blurSculpt::poses, &status);
	MPlug thePosePlug = posesPlug.elementByLogicalIndex(poseIndex, &status);

	MPlug deformationsPlug =  thePosePlug.child(blurSculpt::deformations);
	unsigned int nbDeformations = deformationsPlug.numElements(&status);
	// get the frame indices
	unsigned nEle = deformationsPlug.getExistingArrayAttributeIndices(allFramesIndices_, &status);
	for (unsigned int deformIndex = 0; deformIndex< nbDeformations; deformIndex++)
	{
		MPlug theDeformPlug = deformationsPlug.elementByPhysicalIndex(deformIndex, &status);
		MPlug theFramePlug = theDeformPlug.child(blurSculpt::frame);
		allFramesFloats_.append(theFramePlug.asFloat());
	}
	//MGlobal::displayInfo(MString("\n END query list Poses: \n"));
	return MS::kSuccess;
}

/*
MStatus blurSculptCmd::computeBarycenters() {
	
	// http://tech-artists.org/forum/showthread.php?4907-Maya-API-Vertex-and-Face-matrix-tangent-space

	//This is not a very trivial thing. If you construct the tangents by yourself rather than having maya do it you'll be getting the most stable results. A clean UV map is a requirement however...
	//Maya's mesh lacks a large amount of self awareness, most data is per face-vertex but there is no proper transitioning between vertex and face-vertices and not good way to get averaged data per vertex.
	//Best is to use a MItMeshPolygon to iterate the polygons.
	//MObject sInMeshAttr is the typed kMesh attribute, MDataBlock data is the io data as passed to compute	
	
	MStatus status;
	MFnMesh fnDeformedMesh(meshDeformed_, &status);
	MItMeshPolygon inMeshIter(meshDeformed_);

	MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);

	int initialSize = fnDeformedMesh.numVertices();
	MIntArray parsed (initialSize,-1);
	//Then we need to iterate the individual triangles to get accurate tangent data
	
	MPlug vertexFaceIndicesPlug = blurSculptDepNode.findPlug(blurSculpt::triangleFaceValues);
	MPlug vertexTriangleIndicesPlug = blurSculptDepNode.findPlug(blurSculpt::vertexTriangleIndices);
	
	int triangleInd = 0;
	MPlug trianglePlug, vertexTrianglePlug ,  vertex1Plug, vertex2Plug, vertex3Plug, uValuePlug, vValuePlug;
	MGlobal::displayInfo(MString("\n BaryCenters\n"));

	for (int triangleInd = 0; !inMeshIter.isDone(); inMeshIter.next(), ++triangleInd)
	{	
		// get the trianglePlug		
		trianglePlug = vertexFaceIndicesPlug.elementByLogicalIndex(triangleInd, &status);
		vertex1Plug = trianglePlug.child(blurSculpt::vertex1);
		vertex2Plug = trianglePlug.child(blurSculpt::vertex2);
		vertex3Plug = trianglePlug.child(blurSculpt::vertex3);
		uValuePlug = trianglePlug.child(blurSculpt::uValue);
		vValuePlug = trianglePlug.child(blurSculpt::vValue);
		
		MPointArray points;
		MIntArray vertices;
		inMeshIter.getTriangles(points, vertices);
		MFloatArray u;
		MFloatArray v;
		inMeshIter.getUVs(u, v);
		//Now that we know the points, uvs ad vertex indices per triangle vertex we can start getting the tangent per triangle
		//and use that tangent for all vertices in the triangle. If a vertex is split and has multiple we can only use one of the
		//uv-space-triangles to get a 3D tangent per vertex.
		//
		//This bit iterates each triangle of the poylgon's triangulation (3 points)
		//and extracts the barycentric coordinates for the tangent.
		
		for (unsigned int i = 0; i < vertices.length(); i += 3)
		{
			// Taking UV coordinates [i-(i+2)] as our triangle and
			// the unitX (1,0) as point to get barycentric coordinates for
			// we can get the U direction in barycentric using the function
			// from this site:
			// http://www.blackpawn.com/texts/pointinpoly/
			double u02 = (u[i + 2] - u[i]);
			double v02 = (v[i + 2] - v[i]);
			double u01 = (u[i + 1] - u[i]);
			double v01 = (v[i + 1] - v[i]);
			double dot00 = u02 * u02 + v02 * v02;
			double dot01 = u02 * u01 + v02 * v01;
			double dot11 = u01 * u01 + v01 * v01;
			double d = dot00 * dot11 - dot01 * dot01;
			double u = 1.0;
			double v = 1.0;
			if (d != 0.0)
			{
				u = (dot11 * u02 - dot01 * u01) / d;
				v = (dot00 * u01 - dot01 * u02) / d;
			}
			
			uValuePlug.setDouble(u);
			vValuePlug.setDouble(v);
			vertex1Plug.setInt(vertices[0]);
			vertex2Plug.setInt(vertices[1]);
			vertex3Plug.setInt(vertices[2]);
			
			//Now to get the 3D tangent all we need to do is apply the barycentric coordinates to the 3D points :
			MVector tangent = points[i + 2] * u + points[i + 1] * v - points[i] * (u + v);
			MVector binormal, normal;
			//Next we iterate over the three vertices individually.
			//Here we use MFnMesh::getVertexNormal for the average normal (whether you want angle-weighted depends on what you're doing, I often don't use them).
			//Having the average normal and triangle tangent we can use the cross product for the binormal, cross the normal & binormal again to get a proper
			//perpendicular tangent, because the normal is average and the tangent is not the initial tangent was wrong.
						
			for (unsigned int j = i; j < i + 3; ++j) {
				int theVtx = vertices[j];
				if (parsed[theVtx] == -1) {
					// store the triangle index
					vertexTrianglePlug = vertexTriangleIndicesPlug.elementByLogicalIndex(theVtx, &status);
					vertexTrianglePlug.setValue(triangleInd);					
					//fnDeformedMesh.getVertexNormal(vertices[j], false, normal);
					//binormal = tangent ^ normal;
					//binormal.normalize();
					//tangent = binormal ^ normal;
					//tangent.normalize();
					// store the vertex					
					parsed.set (1, theVtx);
				}				
				//the matrix produced
				//{ {tangent[0], tangent[1], tangent[2], 0},
				//{ binormal[0], binormal[1], binormal[2], 0 },
				//{ normal[0], normal[1], normal[2], 0 },
				//{ point[0], point[1], point[2], 0 }}
				
			}
		}
		
	}
	return MS::kSuccess;
}
*/
MStatus blurSculptCmd::addAPose() {
	MStatus status;
	//MGlobal::displayInfo(MString("\n Function add A Pose : \n") + poseName_);

	MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);
	// get list of poses
	MPlug posesPlug = blurSculptDepNode.findPlug(blurSculpt::poses, &status);
	// get the index of the poseName in the array
	int tmpInd = getMStringIndex(allPosesNames_, poseName_);  //allPosesNames_.indexOf(poseName_);
	int poseIndex;

	//MGlobal::displayInfo(MString("indexOfPoseName : ") + poseIndex);
	bool doAddName = false;
	if (tmpInd == -1) { // if doesn't exists use new one
		poseIndex = GetFreeIndex(posesPlug);
		doAddName = true;
	}else {
		poseIndex = allPosesIndices_[tmpInd];
	}
	if (doAddName) {
		// access the channel 
		MPlug thePosePlug = posesPlug.elementByLogicalIndex(poseIndex, &status);
		// add the channel Name
		MDGModifier dgMod;
		MPlug thePoseMatrixPlug = thePosePlug.child(blurSculpt::poseMatrix);

		MPlug thePoseNamePlug = thePosePlug.child(blurSculpt::poseName);
		thePoseNamePlug.setValue(poseName_);
		MPlug thePoseGainPlug = thePosePlug.child(blurSculpt::poseGain);
		thePoseGainPlug.setValue(1.0);

		MPlug thePoseOffsetPlug = thePosePlug.child(blurSculpt::poseOffset);
		thePoseOffsetPlug.setValue(0.0);

		if (connectTransform_) {
			// add the transform
			//MDagModifier cmd;
			//MGlobal::displayInfo(MString("connection of ") + poseTransformStr_);
			MFnDependencyNode poseTransformDep_(poseTransform_);
			MPlug worldMatPlug = poseTransformDep_.findPlug("matrix");

			dgMod.connect(worldMatPlug, thePoseMatrixPlug);
			dgMod.doIt();
		}
	}
	return MS::kSuccess;

}

MStatus blurSculptCmd::addAFrame() {
	MStatus status;
	//MGlobal::displayInfo(MString("\nadd A Frame\n"));

	// get the meshes access
	MFnMesh fnDeformedMesh(meshDeformed_, &status);
	MFnMesh fnTargetMesh(meshTarget_, &status);
	// get access to our node
	MFnDependencyNode blurSculptDepNode(oBlurSculptNode_);
	// get list of poses
	MPlug posesPlug = blurSculptDepNode.findPlug(blurSculpt::poses, &status);

	// get the nb of vertices
	int nbDeformedVtx = fnDeformedMesh.numVertices();
	int nbTargetVtx = fnTargetMesh.numVertices();

	if (nbDeformedVtx != nbTargetVtx) {
		MGlobal::displayError("not same number of vertices");
		return MS::kFailure;
	}
	//MGlobal::displayInfo(MString("same nb vertices : ") + nbTargetVtx);

	// get the current time
	MTime currentFrame = MAnimControl::currentTime();
	float currentFrameF = float(currentFrame.value());
	//MGlobal::displayInfo(MString("currentFrame : ") + currentFrameF);
	// get the name of the pose
	//MGlobal::displayInfo(MString("poseName : ") + poseName_);
	MGlobal::displayInfo(MString("offset value : ") + aOffset_);

	// get the mode of deformation
	/*
	MPlug deformationTypePlug =  blurSculptDepNode.findPlug(blurSculpt::deformationType, &status);
	int deformationType = deformationTypePlug.asInt();
	*/
	// get the index of the poseName in the array
	int tmpInd = getMStringIndex(allPosesNames_, poseName_); //allPosesNames_.indexOf(poseName_);

	if (tmpInd == -1) { // if doesn't exists create new one
		addAPose(); // add the pose
		getListPoses();// get the list
		int tmpInd = getMStringIndex(allPosesNames_, poseName_); //allPosesNames_.indexOf(poseName_);
	}
	int poseIndex = allPosesIndices_[tmpInd];

	// access the channel 
	MPlug thePosePlug = posesPlug.elementByLogicalIndex(poseIndex, &status);

	// get the Matrix
	MDGModifier dgMod;
	MPoint matPoint(0, 0, 0);
	MPlug thePoseMatrixPlug = thePosePlug.child(blurSculpt::poseMatrix);

	MObject matrixObj;
	thePoseMatrixPlug.getValue(matrixObj);
	MFnMatrixData mData(matrixObj);
	MMatrix matrixValue = mData.matrix(&status);
	matPoint = matPoint * matrixValue;
	MMatrix matrixValueInverse = matrixValue.inverse();
	MPlug poseEnabledPlug = thePosePlug.child(blurSculpt::poseEnabled);

	MPlug deformationTypePlug = thePosePlug.child(blurSculpt::deformationType);
	int deformationType = deformationTypePlug.asInt();

	// get the deformations plug 
	getListFrames(poseIndex);
	MPlug theDeformationPlug = thePosePlug.child(blurSculpt::deformations);

	// we get the list of frames for the pose
	int deformationIndex = -1;
	bool emptyFrameChannel = false;
	for (unsigned int i = 0; i < allFramesFloats_.length(); i++) {
		if (currentFrameF == allFramesFloats_[i]) {
			// work with the indices
			deformationIndex = allFramesIndices_[i];
			emptyFrameChannel = true;
			break;
		}
	}
	
	if (deformationIndex == -1) 
		deformationIndex = GetFreeIndex(theDeformationPlug);

	//MGlobal::displayInfo(MString("deformationIndex : [") + deformationIndex + MString("] frame  : ") + currentFrameF);

	// get the new deformation
	MPlug deformPlug = theDeformationPlug.elementByLogicalIndex(deformationIndex, &status);
	// set the frame value
	MPlug theFramePlug = deformPlug.child(blurSculpt::frame);
	theFramePlug.setValue(currentFrameF);

	MPlug theVectorsPlug = deformPlug.child(blurSculpt::vectorMovements);
	// get the points from the meshes
	MPointArray deformedMeshVerticesPos;
	//first set the gain at 0
	//float prevGainValue = thePoseGainPlug.asFloat();
	//thePoseGainPlug.setValue(0);	
	poseEnabledPlug.setValue(false);
	fnDeformedMesh.getPoints(deformedMeshVerticesPos, MSpace::kObject);

	//then reset the gain to its value
	//thePoseGainPlug.setValue(prevGainValue);

	MPointArray targetMeshVerticesPos;
	fnTargetMesh.getPoints(targetMeshVerticesPos, MSpace::kObject);
	//MItMeshPolygon faceIter(meshDeformed_);
	MPoint offsetPoint;
	MMatrix  mMatrix;



	// if the channel is full first empty it
	/*
	//in python easier
	indices = cmds.getAttr (BSN+".poses[0].deformations[1].vectorMovements", mi=True)
	for ind in indices :     cmds.removeMultiInstance(BSN+".poses[0].deformations[1].vectorMovements[{0}]".format(ind), b=True)
	if (emptyFrameChannel) {
		MGlobal::displayInfo (MString("-->DO empty channel<--") );

		int existingElem = vertexFaceIndicesPlug.numElements();
		for (int indElem = 0; indElem< existingElem; indElem++) {
			MGlobal::displayInfo(MString("    vtx : ") + indElem);
			MPlug oldVectorsPlugElement = vertexFaceIndicesPlug.elementByPhysicalIndex(indElem);
			MFnNumericData fnNumericData;
			MObject vectorValues = fnNumericData.create(MFnNumericData::k3Float, &status);

			//MGlobal::displayInfo (MString("setting ") + offsetPoint.x);
			fnNumericData.setData3Float(0,0,0);
			status = dgMod.newPlugValue(oldVectorsPlugElement, vectorValues);
		}
		dgMod.doIt();

	}

	*/
	MPlug facePlug, vertexPlug, vertexTrianglePlug, triangleValuesPlug;
	MVector normal, tangent, binormal, cross;
	MPoint DFV, TV;

	MFloatVectorArray normals;
	MVectorArray tangents(nbDeformedVtx), smoothTangents(nbDeformedVtx);
	MIntArray tangentFound(nbDeformedVtx, -1); // init at -1

	MVectorArray smoothedNormals (nbDeformedVtx);
	fnDeformedMesh.getVertexNormals(false, normals, MSpace::kWorld);

	
	//smooth the normals
	MItMeshVertex vertexIter(meshDeformed_);
	//MIntArray surroundingVertices;
	MPlug smoothNormalsPlug = blurSculptDepNode.findPlug(blurSculpt::smoothNormals);
	bool useSmoothNormals = smoothNormalsPlug.asBool();
	
	std::vector<MIntArray> perFaceConnectedVertices;
	perFaceConnectedVertices.resize(nbDeformedVtx);
	if (useSmoothNormals) {
		for (int vtxTmp = 0; !vertexIter.isDone(); vertexIter.next(), ++vtxTmp) {
			MIntArray surroundingVertices;
			vertexIter.getConnectedVertices(surroundingVertices);
			perFaceConnectedVertices[vtxTmp] = surroundingVertices;
			int nbSurrounding = surroundingVertices.length();
			//float mult = 1. / (nbSurrounding+1);
			MVector sumNormal = MVector(normals[vtxTmp]);
			for (int k = 0; k < nbSurrounding; ++k) {
				int vtxAround = surroundingVertices[k];
				sumNormal += MVector(normals[vtxAround]);
			}
			//sumNormal = .5*sumNormal + .5*normals[vtxTmp];
			sumNormal.normalize();
			smoothedNormals.set(sumNormal, vtxTmp);
		}
	}
	// Store vectors values
	MPoint zeroPt(0, 0, 0);
	for (int indVtx = 0; indVtx < nbTargetVtx; indVtx++) {
		DFV = deformedMeshVerticesPos[indVtx];
		TV = targetMeshVerticesPos[indVtx];
		if (DFV.distanceTo(TV) > aOffset_) {
			if (deformationType == 0) {
				offsetPoint = TV*matrixValueInverse - DFV*matrixValueInverse;
				//offsetPoint = offsetPoint  * matrixValueInverse + matPoint;				
			}
			else {
				if (tangentFound[indVtx] == -1) {
					tangents.set(getVertexTangent(fnDeformedMesh, vertexIter, indVtx), indVtx);
					tangentFound[indVtx] = 1;
				}
				tangent = tangents[indVtx];
				if (useSmoothNormals) {
					MIntArray surroundingVertices = perFaceConnectedVertices[indVtx];
					int nbSurrounding = surroundingVertices.length();
					for (int k = 0; k < nbSurrounding; ++k) {
						int vtxAround = surroundingVertices[k];
						if (tangentFound[vtxAround] == -1) {
							tangents.set(getVertexTangent(fnDeformedMesh, vertexIter, vtxAround), vtxAround);
							tangentFound[vtxAround] = 1;
						}
						tangent += tangents[vtxAround];
					}
				}
				//fnDeformedMesh.getVertexNormal(indVtx, false, normal);
				if (useSmoothNormals) {
					normal = smoothedNormals[indVtx]; 
				}
				else {
					normal = normals[indVtx];
				}
				tangent.normalize();
				CreateMatrix(zeroPt, normal, tangent, mMatrix);
				offsetPoint = (TV - DFV)* mMatrix.inverse();
			}
			MFnNumericData fnNumericData;
			MObject vectorValues = fnNumericData.create(MFnNumericData::k3Float, &status);

			//MGlobal::displayInfo (MString("setting ") + offsetPoint.x);
			fnNumericData.setData3Float (float(offsetPoint.x), float(offsetPoint.y), float(offsetPoint.z));
			CHECK_MSTATUS_AND_RETURN_IT(status);
			MPlug VectorsPlugElement = theVectorsPlug.elementByLogicalIndex(indVtx, &status);
			CHECK_MSTATUS_AND_RETURN_IT(status);
			status = dgMod.newPlugValue(VectorsPlugElement, vectorValues);
			CHECK_MSTATUS_AND_RETURN_IT(status);
			//MGlobal::displayInfo(MString("vtx : ") + indVtx);
		}
	}
	poseEnabledPlug.setValue(true);
	status = dgMod.doIt();
	CHECK_MSTATUS_AND_RETURN_IT(status);

	return MS::kSuccess;
}

