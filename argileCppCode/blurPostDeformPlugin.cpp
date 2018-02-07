#include "blurPostDeformNode.h"
#include "blurPostDeformCmd.h"

#include <maya/MFnPlugin.h>

//-
// ==========================================================================
// Copyright 2015 Autodesk, Inc.  All rights reserved.
//
// Use of this software is subject to the terms of the Autodesk
// license agreement provided at the time of installation or download,
// or which otherwise accompanies this software in either electronic
// or hard copy form.
// ==========================================================================
//+

////////////////////////////////////////////////////////////////////////
// 
// DESCRIPTION:
//
// Produces the dependency graph node "blurSculptNode".
//
// This plug-in demonstrates how to create a user-defined weighted deformer
// with an associated shape. A deformer is a node which takes any number of
// input geometries, deforms them, and places the output into the output
// geometry attribute. This example plug-in defines a new deformer node
// that blurSculpts vertices according to their CV's weights. The weights are set
// using the set editor or the percent command.
//
// To use this node: 
//	- create a plane or some other object
//	- type: "deformer -type blurSculpt" 
//	- a locator is created by the command, and you can use this locator
//	  to control the direction of the blurSculpt. The object's CV's will be blurSculpt
//	  by the value of the weights of the CV's (the default will be the weight * some constant)
//	  in the direction of the y-vector of the locator 
//	- you can edit the weights using either the component editor or by using
//	  the percent command (eg. percent -v .5 blurSculpt1;) 
//
// Use this script to create a simple example with the blurSculpt node:
// 
//	loadPlugin blurSculptNode;
//	polyTorus -r 1 -sr 0.5 -tw 0 -sx 50 -sy 50 -ax 0 1 0 -cuv 1 -ch 1;
//	deformer -type "blurSculpt";
//	setKeyframe -v 0 -at rotateZ -t 1 transform1;
//	setKeyframe -v 180 -at rotateZ -t 60 transform1;
//	select -cl;

MStatus initializePlugin(MObject obj)
{
	MStatus result;
	MFnPlugin plugin(obj, "blur studios", "1.0", "Any");
	result = plugin.registerNode("blurSculpt", blurSculpt::id, blurSculpt::creator,
		blurSculpt::initialize, MPxNode::kDeformerNode);

	result = plugin.registerCommand(blurSculptCmd::kName, blurSculptCmd::creator, blurSculptCmd::newSyntax);
	CHECK_MSTATUS_AND_RETURN_IT(result);

	MString nodeClassName("blurSculpt");
	MString registrantId("blurPlugin");

	return result;
}

MStatus uninitializePlugin( MObject obj)
{

	MStatus status;
	MFnPlugin plugin( obj );
	status = plugin.deregisterNode(blurSculpt::id );

	MString nodeClassName("blurSculpt");
	MString registrantId("blurPlugin");
	status = plugin.deregisterCommand(blurSculptCmd::kName);
	CHECK_MSTATUS_AND_RETURN_IT(status);

	return status;

}
