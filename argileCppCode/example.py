'''
file -f -new;
unloadPlugin blurPostDeform;





loadPlugin blurPostDeform;

polyTorus -r 1 -sr 0.5 -tw 0 -sx 50 -sy 50 -ax 0 1 0 -cuv 1 -ch 1;
blurSculpt;

polyTorus -r 1 -sr 0.5 -tw 0 -sx 50 -sy 50 -ax 0 1 0 -cuv 1 -ch 1;
select -r pTorus2.vtx[886] ;
move -r -0.710423 1.410621 0.0330195 ;
select -r pTorus2.vtx[845] ;
move -r 0.101498 1.7977 -1.052875 ;
select -cl  ;
move -r 1.398724 0.770505 -2.010649 pTorus2;

select transform1;

'''






from maya import cmds
BSN = "blurSculpt1"


cmds.getAttr (BSN+".poses[0].deformations", mi=True)
cmds.removeMultiInstance(BSN+".poses[0].deformations[1]", b=True)
cmds.blurSculpt (BSN,query = True, listFrames=True, poseName= "testPose")
cmds.blurSculpt (help = True)


cmds.connectAttr ("locator2.worldMatrix", BSN +".poses[0].poseMatrix",f=True)
############################################################################
############################################################################

cmds.blurSculpt ("pTorus1",addAtTime="pTorus2", poseName = "testPose")
BSN = "blurSculpt1"
cmds.listAttr (BSN)
cmds.getAttr (BSN +".poses", mi=True)
cmds.setAttr (BSN +".poses[0].poseOffset",0)


cmds.getAttr (BSN +".poses[0].poseName")
cmds.getAttr (BSN +".poses[0].poseGain")
cmds.getAttr (BSN +".poses[0].poseOffset")

cmds.getAttr (BSN +".poses[0].deformations[0].frame")
cmds.getAttr (BSN +".poses[0].deformations[0].vectorMovements", mi=True)
cmds.getAttr (BSN +".poses[0].deformations[0].vectorMovements[845]")

cmds.blurSculpt (help = True)
cmds.blurSculpt ("pTorus1",query = True, listPoses=True)
cmds.blurSculpt ("pTorus1",query = True, listFrames=True, poseName= "testPose")

cmds.listAttr ("blurSculpt1")


from maya import cmds
BSN = "blurSculpt1"

cmds.currentTime (30)
cmds.blurSculpt ("pTorus1",addAtTime="pTorus2", poseName = "testPose", offset = .002)
cmds.currentTime (70)

cmds.setAttr (BSN +".poses[0].poseGain",0)
cmds.blurSculpt ("pTorus1",addAtTime="pTorus3", poseName = "testPose")
cmds.setAttr (BSN +".poses[0].poseGain",1)

cmds.setAttr (BSN +".poses[0].poseGain",0)
cmds.currentTime (100)
cmds.blurSculpt ("pTorus1",addAtTime="pTorus4", poseName = "testPose")
cmds.setAttr (BSN +".poses[0].poseGain",1)

cmds.blurSculpt (help = True)
cmds.blurSculpt ("pTorus1",query = True, listPoses=True)
cmds.blurSculpt ("pTorus1",query = True, listFrames=True, poseName= "testPose")


cmds.setAttr (BSN +".poses[0].deformations[3].frame",50)


