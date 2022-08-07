#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================

from mathutils import *
from math import *
from bpy.props import *
import bpy
import bmesh
import os
import sys
import math


# Version history
# 1.0.0 - 2022-05-11: Original version.
# 1.0.1 - 2022-05-12: Misc cleanup
# 1.0.2 - 2022-05-15: Before it executes the main function, the add-on now checks to make sure we're feeding it an armature object (since we can't filter it at the UI level).
# 1.0.3 - 2022-08-07: Misc formatting cleanup before uploading to GitHub.

###############################################################################
SCRIPT_NAME = 'understudy_creator'

# This Blender add-on creates a lightweight render-able mesh character based on
# a Rigify metarig.
# This can be helpful in roughing out animation before a real character has
# been designed, like when creating a 3D animatic.
###############################################################################

bl_info = {
    "name": "Understudy Creator",
    "author": "Jeff Boller",
    "version": (1, 0, 3),
    "blender": (2, 93, 0),
    "location": "View3D > Properties > Rigging",
    "description": "Creates a lightweight renderable character based on a Rigify rig",
    "wiki_url": "https://github.com/sundriftproductions/blenderaddon-understudy-creator/wiki",
    "tracker_url": "https://github.com/sundriftproductions/blenderaddon-understudy-creator",
    "category": "3D View"
}

def GetPoseBoneLocationWORLD(poseBone, tip = False): # Returns the WORLD bone location, as if we wanted to put an object at that same location as the bone in world space.
    if tip:
        offset = 1 # 0 = fat end of the bone, 1 = skinny end of the bone
    else:
        offset = 0

    T = Matrix.Translation(offset * (poseBone.tail - poseBone.head))
    # Now get the object from the pose bone.
    obj = poseBone.id_data
    matrix_final = obj.matrix_world @ (T @ poseBone.matrix)
    loc, rot, scale = matrix_final.decompose()
    return loc

def GetPoseBoneRotationWORLD(poseBone): # Returns the WORLD bone rotation, as if we wanted to put an object with the same rotation as the bone in world space.
    loc, rot, scale = poseBone.matrix.decompose()
    return rot

def add_fake_bone(loc_start, loc_end, rot):
    dir = os.path.dirname(os.path.realpath(__file__)) + '/understudy_PUB.blend/Object/'
    dir = dir.replace("\\", "/")  # Replace all of the backslashes in our path with forward slashes. This will still work on Windows if you don't do this, but this is just to be consistent.
    fp = 'understudy_PUB.blend'

    bone_length = fabs(sqrt(math.pow(loc_start[0]-loc_end[0], 2) + math.pow(loc_start[1]-loc_end[1], 2) + math.pow(loc_start[2]-loc_end[2], 2)))

    old_objs = set(bpy.context.scene.objects) # Keep track of all of our objects before importing.
    bpy.ops.wm.append(filepath=fp, directory=dir, files=[{'name': 'understudy_fake_bone'}])
    imported_objs = set(bpy.context.scene.objects) - old_objs # Now figure out which objects we imported...
    for o in imported_objs:
        o.scale[0] = bone_length
        o.scale[1] = bone_length
        o.scale[2] = bone_length
        o.location = loc_start
        o.rotation_quaternion = rot
        return o.name
        break

def select_name(obj_name, extend = True):
    if extend == False:
        bpy.ops.object.select_all(action='DESELECT')
    ob = bpy.data.objects.get(obj_name)
    ob.select_set(state=True)
    bpy.context.view_layer.objects.active = ob

class UNDERSTUDYCREATOR_PT_CreateUnderstudy(bpy.types.Operator):
    bl_idname = "crund.create_understudy"
    bl_label = "Create Understudy"
    bl_options = {"REGISTER", "UNDO"}  # Required for when we do a bpy.ops.ed.undo_push(), otherwise Blender will crash when you try to undo the action in this class.

    def execute(self, context):
        bpy.ops.ed.undo_push()  # Manually record that when we do an undo, we want to go back to this exact state.

        self.report({'INFO'}, '**********************************')
        self.report({'INFO'}, SCRIPT_NAME + ' - START')

        # Make sure we have valid parameters.
        stored_understudy_armature_name = bpy.context.preferences.addons['understudy_creator'].preferences.understudy_armature_name

        if bpy.data.objects.get(stored_understudy_armature_name) is None:
            self.report({'ERROR'}, '  ERROR: The armature "' + stored_understudy_armature_name + '" in not in the scene. Aborting.')
            return {'CANCELLED'}

        if bpy.data.objects.get(stored_understudy_armature_name).type != "ARMATURE":
            self.report({'ERROR'}, '  ERROR: The object "' + stored_understudy_armature_name + '" in not an armature. Aborting.')
            return {'CANCELLED'}

        original_mode = bpy.context.active_object.mode

        newobjs = []

        for b in bpy.data.objects[stored_understudy_armature_name].pose.bones:
            loc_fat_end = GetPoseBoneLocationWORLD(b, False)
            loc_tip = GetPoseBoneLocationWORLD(b, True)
            rot = GetPoseBoneRotationWORLD(b)

            print(b.name)
            print("  fat end location: " + str(loc_fat_end))
            print("      tip location: " + str(loc_tip))
            print("          rotation: " + str(rot))
            print()

            newobjs.append(add_fake_bone(loc_fat_end, loc_tip, rot))

        # Now combine all of our imported objects into one "big" object.
        print()
        print("newobjs: " + str(newobjs))

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        joined_name = ''
        for obj_name in newobjs:
            joined_name = obj_name # Not the most efficient way to do this, but I want to know the last object selected, because that will be the name of the joined object.
            select_name(obj_name)
        bpy.ops.object.join()

        # Now rename the joined object to something useful.
        bpy.data.objects[joined_name].name = "understudy_" + stored_understudy_armature_name

        try:
            bpy.context.active_object.mode = original_mode
        except:
            pass

        self.report({'INFO'}, SCRIPT_NAME + ' - END')
        self.report({'INFO'}, '**********************************')
        self.report({'INFO'}, 'Done running script ' + SCRIPT_NAME)

        return {'FINISHED'}

class UnderstudyCreatorPreferencesPanel(bpy.types.AddonPreferences):
    bl_idname = __module__
    understudy_armature_name: bpy.props.StringProperty(name = 'Metarig', default = '', description = 'The Rigify metarig that will be turned into an understudy')

class UNDERSTUDYCREATOR_PT_Main(bpy.types.Panel):
    bl_idname = "UNDERSTUDYCREATOR_PT_Main"
    bl_label = "Understudy Creator"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Rigging"

    def draw(self, context):
        row = self.layout.row(align=True)
        row.prop_search(bpy.context.preferences.addons['understudy_creator'].preferences, "understudy_armature_name", bpy.data, "objects", icon='OUTLINER_OB_ARMATURE')

        row = self.layout.row(align=True)
        row = self.layout.row(align=True)
        self.layout.operator("crund.create_understudy",icon='OUTLINER_OB_ARMATURE')

def register():
    bpy.utils.register_class(UnderstudyCreatorPreferencesPanel)
    bpy.utils.register_class(UNDERSTUDYCREATOR_PT_CreateUnderstudy)
    bpy.utils.register_class(UNDERSTUDYCREATOR_PT_Main)

def unregister():
    bpy.utils.unregister_class(UnderstudyCreatorPreferencesPanel)
    bpy.utils.unregister_class(UNDERSTUDYCREATOR_PT_CreateUnderstudy)
    bpy.utils.unregister_class(UNDERSTUDYCREATOR_PT_Main)

if __name__ == "__main__":
    register()
