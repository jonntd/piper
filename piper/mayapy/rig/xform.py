#  Copyright (c) Christian Corsica. All Rights Reserved.

import pymel.core as pm

import piper.config as pcfg
import piper.config.maya as mcfg
import piper.core.namer as namer

import piper.mayapy.convert as convert
import piper.mayapy.mayamath as mayamath
import piper.mayapy.attribute as attribute
import piper.mayapy.pipernode as pipernode
import piper.mayapy.selection as selection
import piper.mayapy.manipulator as manipulator


def isUniformlyScaled(transform):
    """
    Returns whether the given is uniformly scaled or not.

    Args:
        transform (pm.nodetypes.Transform): Transform to check for uniform scale.

    Returns:
        (boolean): True if all scale values are the same in all axis.
    """
    return round(transform.sx.get(), 3) == round(transform.sy.get(), 3) == round(transform.sz.get(), 3)


def toOffsetMatrix(transform):
    """
    Convenience method for moving the matrix of a transform to the offset matrix and zeroing out the values.
    Similar to makeIdentity or Freeze Transforms, except values end up in offsetParentMatrix.

    Args:
        transform (pm.nodetypes.Transform): Transform to zero out.
    """
    transform.offsetParentMatrix.set(transform.matrix.get())
    mayamath.zeroOut(transform)


def parent(transforms=None, world=False):
    """
    Parents transforms to the last given transform and gets rid of joint orient values if transform is a joint.

    Args:
        transforms (list or pm.nodetypes.DependNode): Transforms to parent. Last transform is the parent of the rest.
        Minimum of two objects.

        world (boolean): If True, will parent all the given transforms to world
    """
    transforms = selection.validate(transforms, minimum=1)

    if world:
        for transform in transforms:

            if isinstance(transform, pm.nodetypes.Joint):
                matrix = transform.worldMatrix.get()
                pm.parent(transform, w=True)
                transform.jointOrient.set(0, 0, 0)
                pm.xform(transform, ws=True, m=matrix)
            else:
                pm.parent(transform, w=True)
    else:
        for transform in transforms[:-1]:

            if isinstance(transform, pm.nodetypes.Joint):
                matrix = transform.worldMatrix.get()
                pm.parent(transform, transforms[-1])
                transform.jointOrient.set(0, 0, 0)
                pm.xform(transform, ws=True, m=matrix)
            else:
                pm.parent(transform, transforms[-1])


def getChain(start, end=None):
    """
    Gets all the transforms parented between the given start and end transforms, inclusive.

    Args:
        start (pm.nodetypes.Transform): Top parent of the chain.

        end (pm.nodetypes.Transform): The child to end search at. If none given, will return only the given start.

    Returns:
        (list): All the transforms between given start and given end, including the given transforms in order.
    """
    if not end:
        return [start]

    parents = end.getAllParents()

    if start not in parents:
        pm.error(start.nodeName() + ' is not a parent of: ' + end.nodeName())

    parents.reverse()
    start_index = parents.index(start)
    chain = parents[start_index:]
    chain.append(end)
    return chain


def duplicateChain(chain, prefix='new_', color='default', scale=1.0):
    """
    Duplicates the given chain, renames it, and parents it to the world.

    Args:
        chain (list): Transforms to duplicate.

        prefix (string): Prefix to add to duplicate transforms.

        color (string): Color to set the duplicate chain.

        scale (float): Scale to multiply radius attribute by.

    Returns:
        (list): Duplicated transforms with new name.
    """
    new_chain = pm.duplicate(chain, parentOnly=True, renameChildren=True)

    start = new_chain[0]
    parent([start], world=True)
    start.overrideEnabled.set(True)
    start.overrideColor.set(convert.colorToInt(color))

    for original, duplicate in zip(chain, new_chain):
        duplicate.rename(prefix + original.name(stripNamespace=True))
        [original.attr(attr) >> duplicate.attr(attr) for attr in mcfg.bind_attributes if original.hasAttr(attr)]

        if duplicate.hasAttr('radius'):
            duplicate.radius.set(duplicate.radius.get() * scale)

    return new_chain


def getOrigShape(transform):
    """
    Creates the Orig Shape used by deformers.

    Args:
        transform (pm.nodetypes.Transform): Transform to create orig shape of.

    Returns:
        (pm.nodetypes.Mesh): Shape created.
    """
    shape = pm.deformableShape(transform, og=True)
    shape = list(filter(None, shape))

    if shape:
        return shape[0]

    return pm.deformableShape(transform, cog=True)[0].node()


def mirrorTranslate(transforms=None, axis=pcfg.default_mirror_axis, swap=None, duplicate=True):
    """
    Mirrors the given transforms across the given axis set up to be used as a mirror translate transform.

    Args:
        transforms (list): Transforms to mirror across given axis.

        axis (string): Name of axis to mirror across.

        swap (list): Text to swap with each other for duplicates name.

        duplicate (boolean): If True will duplicate transforms before mirroring. Else will mirror the given transforms.

    Returns:
        (list): Transforms mirrored.
    """
    transforms = selection.validate(transforms)
    axis_vector = convert.axisToVector(axis, absolute=True)
    mirrored_axis = [value * -1 for value in axis_vector]
    mirrored_axis.append(1)
    to_mirror = []

    if swap is None:
        swap = [pcfg.left_suffix, pcfg.right_suffix]

    if duplicate:
        for transform in transforms:
            name = transform.nodeName()
            new_name = namer.swapText(name, *swap)
            new_transform = pm.duplicate(transform, ic=False, un=False, n=new_name)[0]
            to_mirror.append(new_transform)
    else:
        to_mirror = transforms

    for transform in to_mirror:
        matrix = transform.worldMatrix.get()
        identity = [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]
        mirrored_matrix = [m * a if m != 0 and a != 0 else m for row in identity for m, a in zip(row, mirrored_axis)]
        mirrored_matrix = matrix * pm.dt.Matrix(mirrored_matrix)
        pm.xform(transform, ws=True, m=mirrored_matrix)
        [transform.attr('s' + axis).set(abs(transform.attr('s' + axis).get())) for axis in ['x', 'y', 'z']]

    return to_mirror


def mirrorRotate(transforms=None, axis=pcfg.default_mirror_axis, swap=None):
    """
    Mirrors the given transforms across the given axis set up to be used as a mirror rotate transform.

    Args:
        transforms (list): Transforms to mirror across given axis.

        axis (string): Name of axis to mirror across.

        swap (list): Words to search and replace. Will search for first index, and replace with second index.

    Returns:
        (list): Joints that were mirrored. Note that all their children get mirrored as well.
    """
    mirrored_transforms = []
    transforms = selection.validate(transforms)
    options = {'mxy': False, 'myz': False, 'mxz': False, 'mb': True, 'sr': swap}

    if axis == 'x':
        options['myz'] = True
    elif axis == 'y':
        options['mxz'] = True
    elif axis == 'z':
        options['mxy'] = True
    else:
        pm.error('No valid axis given. Pick "x", "y", or "z".')

    for transform in transforms:
        name = transform.nodeName()

        if not swap:
            if name.endswith(pcfg.left_suffix):
                options['sr'] = [pcfg.left_suffix, pcfg.right_suffix]
            elif name.endswith(pcfg.right_suffix):
                options['sr'] = [pcfg.right_suffix, pcfg.left_suffix]
            else:
                options['sr'] = ['', '']

        mirrored_joint = pm.mirrorJoint(transform, **options)[0]
        mirrored_joint = pm.PyNode(mirrored_joint)
        mirrored_transforms.append(mirrored_joint)
        joint_parent = mirrored_joint.getParent()

        if joint_parent:
            pm.parent(mirrored_joint, w=True)
            parent([mirrored_joint, joint_parent])

    return mirrored_transforms


def interceptConnect(source, target, name='', operation=1):
    """
    Intercepts the given target and adds, subtracts or averages it with give source.

    Args:
        source (pm.general.Attribute): Source attribute to connect into interception.

        target (pm.general.Attribute): Target attribute to intercept and get plug connection from.

        name (string): Name of intercept node.

        operation (int): 1 is add, 2 is subtract, 3 is average.
    """
    if operation and target.connections(scn=True, plugs=True, destination=False):
        connection = target.connections(scn=True, plugs=True, destination=False)[0]
        plus = pm.createNode('plusMinusAverage', n=name)
        plus.operation.set(operation)
        connection >> plus.input3D[0]
        source >> plus.input3D[1]
        plus.output3D >> target
    else:
        source >> target


def parentMatrixConstraint(driver=None, target=None,
                           t=True, r=True, s=True,
                           offset=False, jo=False, intercept=None, message=False):
    """
    Creates a parent matrix constraint between given driver and target. Could use selected objects too.
    Shout-out to Jarred Love for his tutorials.

    Args:
        driver (pm.nodetypes.Transform): Transform that will drive the given target

        target (pm.nodetypes.Transform): Transform that will be driven by given driver.

        t (boolean): If True, will connect translate channel to be driven.

        r (boolean): If True, will connect rotate channel to be driven.

        s (boolean): If True, will connect scale channel to be driven.

        offset (boolean): If True, will maintain current transform relation between given driver and target.

        jo (boolean): If True, AND given target transform has non-zero joint orient values,
        will create extra nodes to account for such values. Else will set joint orient values to zero.

        intercept (int): If not zero and target plugs already have connections. Will add or subtract depending on int.

        message (boolean) If True, will add message attribute that states connection between driver and target.

    Returns:
        (pm.nodetypes.DependNode): Decompose Matrix that drives target.
    """
    if not driver or not target:
        selected = pm.selected()

        if len(selected) < 2:
            pm.error('Not enough items selected and no driver or target found!')

        driver = selected[-2]
        target = selected[-1]

    name = target.name(stripNamespace=True)
    driver_name = driver.name(stripNamespace=True)

    if all([t, r, s]):
        mult_name = '_'.join([name, mcfg.parent_matrix_mult_suffix])
    else:
        middle = ''
        if t:
            middle += 'T'
        if r:
            middle += 'R'
        if s:
            middle += 'S'

        mult_name = '_'.join([name, middle, mcfg.parent_matrix_mult_suffix])

    matrix_multiplication = pm.createNode('multMatrix', n=mult_name)
    decomp_matrix = pm.createNode('decomposeMatrix', n=driver_name + '_to_' + name + mcfg.parent_matrix_decomp_suffix)

    if offset:
        offset = target.worldMatrix.get() * driver.worldInverseMatrix.get()
        matrix_multiplication.matrixIn[0].set(offset)
        driver.worldMatrix[0] >> matrix_multiplication.matrixIn[1]
        target.parentInverseMatrix[0] >> matrix_multiplication.matrixIn[2]
    else:
        driver.worldMatrix[0] >> matrix_multiplication.matrixIn[0]
        target.parentInverseMatrix[0] >> matrix_multiplication.matrixIn[1]

    matrix_multiplication.matrixSum >> decomp_matrix.inputMatrix

    if t:
        plus_name = driver_name + '_plusTranslate_' + name
        interceptConnect(decomp_matrix.outputTranslate, target.translate, plus_name, intercept)

    if r:
        if target.hasAttr('jointOrient') and target.jointOrient.get() != pm.dt.Vector(0, 0, 0):
            if jo:
                compose_matrix = pm.createNode('composeMatrix', n=name + mcfg.parent_matrix_rot_comp_suffix)
                compose_matrix.inputRotate.set(target.jointOrient.get())
                target_parent = target.getParent()

                if target_parent:
                    mult_rot_matrix = pm.createNode('multMatrix', n=name + mcfg.parent_matrix_rot_mult_suffix)
                    compose_matrix.outputMatrix >> mult_rot_matrix.matrixIn[0]
                    target_parent.worldMatrix >> mult_rot_matrix.matrixIn[1]
                    joint_orient_matrix_output = mult_rot_matrix.matrixSum
                else:
                    joint_orient_matrix_output = compose_matrix.outputMatrix

                inverse_matrix = pm.createNode('inverseMatrix', n=name + mcfg.parent_matrix_rot_inv_suffix)
                joint_orient_matrix_output >> inverse_matrix.inputMatrix

                mult_rot_matrix = pm.createNode('multMatrix', n=name + mcfg.parent_matrix_rot_mult_suffix)

                if offset:
                    offset = target.worldMatrix.get() * driver.worldInverseMatrix.get()
                    mult_rot_matrix.matrixIn[0].set(offset)
                    driver.worldMatrix >> mult_rot_matrix.matrixIn[1]
                    inverse_matrix.outputMatrix >> mult_rot_matrix.matrixIn[2]
                else:
                    driver.worldMatrix >> mult_rot_matrix.matrixIn[0]
                    inverse_matrix.outputMatrix >> mult_rot_matrix.matrixIn[1]

                rotate_decompose = pm.createNode('decomposeMatrix', n=name + mcfg.parent_matrix_rot_decomp_suffix)
                mult_rot_matrix.matrixSum >> rotate_decompose.inputMatrix
                output_rotate = rotate_decompose.outputRotate

            else:
                target.jointOrient.set((0, 0, 0))
                output_rotate = decomp_matrix.outputRotate

        else:
            output_rotate = decomp_matrix.outputRotate

        plus_name = driver_name + '_plusRotate_' + name
        interceptConnect(output_rotate, target.rotate, plus_name, intercept)

    if s:
        plus_name = driver_name + '_plusScale_' + name
        interceptConnect(decomp_matrix.outputScale, target.scale, plus_name, intercept)

    if message:
        attribute.addDrivenMessage(driver, target)

    return decomp_matrix


def offsetConstraint(driver, target, t=True, r=True, s=True, offset=False, plug=True, message=False):
    """
    Parents constraint the given target by driving it through the offset Parent Matrix plug with the given driver.

    Args:
        driver (pm.nodetypes.Transform): Transform that will drive the given target through the constraint.

        target (pm.nodetypes.Transform): Transform that will be driven by the given driver through the constraint.

        t (boolean): If True, translate channels will be driven.

        r (boolean): If True, translate channels will be driven.

        s (boolean): If True, translate channels will be driven.

        offset (boolean): If True, will maintain offset when creating constraint.

        plug (boolean): If True, will plug output into target's offset parent matrix attribute.

        message (boolean) If True, will add message attribute that states connection between driver and target.
    """
    target_parent = target.getParent()
    target_name = target.name(stripNamespace=True)
    driver_name = driver.name(stripNamespace=True)

    if target_parent and offset:
        matrix_mult = pm.createNode('multMatrix', name=target_name + mcfg.offset_and_parent_mult_suffix)
        offset = target.worldMatrix.get() * driver.worldInverseMatrix.get()
        matrix_mult.matrixIn[0].set(offset)
        driver.worldMatrix >> matrix_mult.matrixIn[1]
        target_parent.worldInverseMatrix >> matrix_mult.matrixIn[2]
        output = matrix_mult.matrixSum
    elif target_parent:
        matrix_mult = pm.createNode('multMatrix', name=target_name + mcfg.offset_parent_mult_suffix)
        driver.worldMatrix >> matrix_mult.matrixIn[0]
        target_parent.worldInverseMatrix >> matrix_mult.matrixIn[1]
        output = matrix_mult.matrixSum
    elif offset:
        matrix_mult = pm.createNode('multMatrix', name=target_name + mcfg.offset_only_mult_suffix)
        offset = target.worldMatrix.get() * driver.worldInverseMatrix.get()
        matrix_mult.matrixIn[0].set(offset)
        driver.worldMatrix >> matrix_mult.matrixIn[1]
        output = matrix_mult.matrixSum
    else:
        output = driver.worldMatrix

    # if all attribute are True OR all attributes are False, don't decompose, plug output into offset parent matrix.
    if all([t, r, s]) or not any([t, r, s]):
        pass
    else:
        matrix_prefix = driver_name + '_to_' + target_name
        decomp_matrix = pm.createNode('decomposeMatrix', n=matrix_prefix + mcfg.offset_parent_decomp_suffix)
        comp_matrix = pm.createNode('composeMatrix', n=matrix_prefix + mcfg.offset_parent_comp_suffix)
        output >> decomp_matrix.inputMatrix

        if t:
            decomp_matrix.outputTranslate >> comp_matrix.inputTranslate
        if r:
            decomp_matrix.outputRotate >> comp_matrix.inputRotate
        if s:
            decomp_matrix.outputScale >> comp_matrix.inputScale

        output = comp_matrix.outputMatrix

    if plug:
        output >> target.offsetParentMatrix
        mayamath.zeroOut(target)

    if message:
        attribute.addDrivenMessage(driver, target)

    return output


def aimConstraint(target, up, driven):
    """
    Creates an aim constraint with the given driven transform aiming at the given target transform.

    Args:
        target (pm.nodetypes.Transform): Transform to aim at.

        up (pm.nodetypes.Transform): Transform to aim the up axis to.

        driven (pm.nodetypes.Transform): Transform that will be rotated to aim at the given target.

    Returns:
        (pm.nodetypes.AimMatrix): Aim matrix node used to aim given driven at given target.
    """
    offset_plug = attribute.getSourcePlug(driven.offsetParentMatrix)
    parent_plug = offset_plug if offset_plug else driven.parentMatrix

    driven_name = driven.name(stripNamespace=True)
    driven_compose = pm.createNode('composeMatrix', n=driven_name + '_T' + mcfg.compose_matrix_suffix)
    driven.translate >> driven_compose.inputTranslate

    mult_matrix = pm.createNode('multMatrix', n=driven_name + '_parent' + mcfg.mult_matrix_suffix)
    driven_compose.outputMatrix >> mult_matrix.matrixIn[0]
    parent_plug >> mult_matrix.matrixIn[1]

    aim_matrix_name = driven_name + '_TO_' + target.name(stripNamespace=True) + mcfg.aim_matrix_suffix
    aim_matrix = pm.createNode('aimMatrix', n=aim_matrix_name)
    mult_matrix.matrixSum >> aim_matrix.inputMatrix

    aim_axis = mayamath.getOrientAxis(driven, target)
    up_axis = mayamath.getOrientAxis(driven, up)

    aim_matrix.secondaryMode.set(1)
    aim_matrix.primaryInputAxis.set(aim_axis)
    aim_matrix.secondaryInputAxis.set(up_axis)
    target.worldMatrix >> aim_matrix.primaryTargetMatrix
    up.worldMatrix >> aim_matrix.secondaryTargetMatrix

    attribute.addSeparator(driven)
    driven.addAttr(mcfg.bendy_aim_attribute, k=True, dv=1, hsx=True, hsn=True, smn=0, smx=1)

    if offset_plug:
        blend_matrix = pm.createNode('blendMatrix', n=driven + mcfg.aim_matrix_suffix + mcfg.blend_matrix_suffix)
        offset_plug >> blend_matrix.inputMatrix
        aim_matrix.outputMatrix >> blend_matrix.target[0].targetMatrix
        driven.attr(mcfg.bendy_aim_attribute) >> blend_matrix.target[0].weight
        blend_matrix.outputMatrix >> driven.offsetParentMatrix
    else:
        driven.attr(mcfg.bendy_aim_attribute) >> aim_matrix.envelope
        aim_matrix.outputMatrix >> driven.offsetParentMatrix

    return aim_matrix


def poleVectorMatrixConstraint(ik_handle, control):
    """
    Creates a pole vector matrix constraint from the given ik_handle's start joint driven by the given pole vector ctrl.
    Thanks to Wasim Khan for this method.
    https://github.com/wasimk/maya-pole-vector-constaint

    Args:
        ik_handle (pm.nodetypes.IkHandle): IK Handle that will be driven by pole vector control.

        control (pm.nodetypes.Transform): Control that will drive the ik_handle rotations.

    Returns:
        (list): All nodes created.
    """
    if ik_handle.nodeType() != 'ikHandle':
        pm.error(ik_handle.nodeName() + ' is not an IK Handle!')

    attribute.addSeparator(control)
    pm.addAttr(control, at='float', ln='poleVectorWeight', dv=1, min=0, max=1, k=True, w=True, r=True)
    joint = pm.PyNode(pm.ikHandle(ik_handle, q=True, startJoint=True))

    # First create all necessary nodes needed for pole vector math
    world_point = pm.createNode('pointMatrixMult', name='{}_Position_PointMatrixMult'.format(joint))
    compose_matrix = pm.createNode('composeMatrix', name='{}_Position_CompMatrix'.format(joint))
    inverse_matrix = pm.createNode('inverseMatrix', name='{}_Position_InverseMatrix'.format(joint))
    multiplication_matrix = pm.createNode('multMatrix', name='{}_PolePosition_MultMatrix'.format(ik_handle))
    pole_matrix = pm.createNode('pointMatrixMult', name='{}_PolePosition_PointMatrixMult'.format(ik_handle))
    blend_colors = pm.createNode('blendColors', name='{}_Blend_PoleWeight'.format(ik_handle))
    blend_colors.color2.set(ik_handle.poleVector.get())

    # Since ikHandle is setting rotation value on startJoint, we can't connect worldMatrix right away.
    # In order to avoid cycle, Compose world space position for start joint with pointMatrixMult node
    # Connecting position attribute and parentMatrix will give us worldSpace position
    joint.translate >> world_point.inPoint
    joint.parentMatrix >> world_point.inMatrix

    # Now composeMatrix from output, so we can inverse and find local position from startJoint to pole control
    world_point.output >> compose_matrix.inputTranslate
    compose_matrix.outputMatrix >> inverse_matrix.inputMatrix
    control.worldMatrix >> multiplication_matrix.matrixIn[0]
    inverse_matrix.outputMatrix >> multiplication_matrix.matrixIn[1]

    # Now connect outputs
    multiplication_matrix.matrixSum >> pole_matrix.inMatrix
    pole_matrix.output >> blend_colors.color1
    blend_colors.output >> ik_handle.poleVector
    control.poleVectorWeight >> blend_colors.blender

    return [blend_colors, pole_matrix, multiplication_matrix, inverse_matrix, compose_matrix, world_point]


def calculatePoleVector(start_transform, mid_transform, end_transform, scale=1, forward=True):
    """
    Props to Greg Hendrix for walking through the math: https://vimeo.com/240328348

    Args:
        start_transform (PyNode): Start of the joint chain

        mid_transform (PyNode): Mid joint of the chain.

        end_transform (PyNode): End joint of the chain.

        scale (float): How far away should the pole vector position be compared to the chain length.

        forward (Any): Node or list to convert to vector direction to move pole vector if chain is in straight line.

    Returns:
        (list): Transform of pole vector control. Translation as first index, rotation as second, scale as third.
    """
    is_in_straight_line = False
    zero_vector = pm.dt.Vector(0, 0, 0)

    # if transform has rotations or joint orient, then its not in a straight line and we can figure out pole vector
    if mid_transform.r.get().isEquivalent(zero_vector, tol=0.5):
        if mid_transform.hasAttr('orientJoint'):
            if mid_transform.orientJoint.get().isEquivalent(zero_vector, tol=0.5):
                is_in_straight_line = True
        else:
            is_in_straight_line = True

    # if transform is in a straight line use the location of the mid transform to place the pole vector
    if is_in_straight_line:
        translation = pm.dt.Vector(pm.xform(mid_transform, q=True, ws=True, t=True))
        rotation = pm.xform(mid_transform, q=True, ws=True, ro=True)

        if forward:
            forward = [0, 0, 1] if forward is True else forward
            forward = convert.toVector(forward)
            distance = mayamath.getDistance(start_transform, end_transform)
            forward = forward * (distance * scale)
            translation = translation + forward

    else:
        start = pm.dt.Vector(pm.xform(start_transform, q=True, ws=True, t=True))
        mid = pm.dt.Vector(pm.xform(mid_transform, q=True, ws=True, t=True))
        end = pm.dt.Vector(pm.xform(end_transform, q=True, ws=True, t=True))

        start_to_end = end - start
        start_to_mid = mid - start

        start_to_end_length = start_to_end.length()
        mid_scale = start_to_end.dot(start_to_mid) / (start_to_end_length * start_to_end_length)
        mid_chain_point = start + start_to_end * mid_scale

        chain_length = (mid - start).length() + (end - mid).length()
        translation = (mid - mid_chain_point).normal() * chain_length * scale + mid
        rotation = mayamath.getAimRotation(mid_chain_point, translation)

    single_scale = mid_transform.radius.get() if mid_transform.hasAttr('radius') else 1
    scale = [single_scale, single_scale, single_scale]

    return translation, rotation, scale, is_in_straight_line


def squashStretch(source, output, attribute_name='s', axis='y'):
    """
    Hooks up given source attribute to given output node's given attribute_name with the reciprocal value to other axis.

    Args:
        source (pm.general.Attribute): Attribute that will drive squash and stretch behavior.

        output (pm.nodetypes.DependNode): Node that source and its reciprocals will hook onto.

        attribute_name (string): Name of compound attribute to connect to.

        axis (string): Name of axis that will be driven one to one with given source.

    Returns:
        (pm.nodetypes.piperReciprocal): Reciprocal node created for squash and stretch values.
    """
    # connect driving axis
    tri_axis = convert.axisToTriAxis(axis, absolute=True)
    source >> output.attr(attribute_name + axis)

    # connect other axis as reciprocals
    reciprocal = pipernode.reciprocal(source)
    reciprocal.output >> output.attr(attribute_name + tri_axis[1])
    reciprocal.output >> output.attr(attribute_name + tri_axis[2])

    return reciprocal


def orientToTransform(driver, target, condition=True):
    """
    Orients the given target to have the same orientation as the given driver. Same as doing an orient constraint.

    Args:
        driver (pm.nodetypes.Transform): Transform to get rotation from.

        target (pm.nodetypes.Transform): Transform to paste rotation onto.

        condition (boolean): Convenience arg for whether to perform operation or not.
    """
    if not condition:
        return

    rotation = pm.xform(driver, q=True, ws=True, ro=True)
    pm.xform(target, ws=True, ro=rotation)


def orientToVertex(transform, vertex, position=None, condition=True):
    """
    Orients the given transform to the given vertex's normal. Up/Side orientation is likely to be random.

    Args:
        transform (pm.nodetypes.Transform): Node to orient to given vertex.

        vertex (pm.general.MeshVertex): Vertex to get normal from.

        position (pm.dt.Vector or list): transform location.

        condition (boolean): Convenience arg for whether to perform operation or not.
    """
    if not condition:
        return

    if not position:
        position = pm.xform(transform, q=True, ws=True, t=True)

    neighbor = vertex.connectedVertices()
    neighbor = neighbor.indices()[0] if isinstance(neighbor, pm.general.MeshVertex) else neighbor[0].indices()[0]
    neighbor = pm.PyNode(vertex.node().name() + '.vtx[{}]'.format(str(neighbor)))
    up = mayamath.getDirection(position, neighbor.getPosition(space='world'))

    normal = vertex.getNormal(space='world')
    matrix = mayamath.getMatrixFromVector(normal, up, location=position)
    pm.xform(transform, ws=True, m=matrix)
    transform.s.set((1, 1, 1))


def orientToEdge(transform, edge, position=None, condition=True):
    """
    Orients the given transform to the given edge's direction and normal.

    Args:
        transform (pm.nodetypes.Transform): Node to orient to given vertex.

        edge (pm.general.MeshEdge): Edge to get vertices direction and normals from.

        position (pm.dt.Vector or list): transform location.

        condition (boolean): Convenience arg for whether to perform operation or not.
    """
    if not condition:
        return

    if not position:
        position = pm.xform(transform, q=True, ws=True, t=True)

    vertices = edge.connectedVertices()
    vertex_positions = [vertex.getPosition(space='world') for vertex in vertices]

    direction = vertices[0].getNormal('world') + vertices[-1].getNormal('world')
    up = mayamath.getDirection(*vertex_positions)
    matrix = mayamath.getMatrixFromVector(direction, up, location=position)
    pm.xform(transform, ws=True, m=matrix)


def orientToFace(transform, face, position=None, condition=True):
    """
    Orients the given transform to the given face's normal.

    Args:
        transform (pm.nodetypes.Transform): Node to orient to given vertex.

        face (pm.general.MeshFace): Face to get normal from.

        position (pm.dt.Vector or list): transform location.

        condition (boolean): Convenience arg for whether to perform operation or not.
    """
    if not condition:
        return

    if not position:
        position = pm.xform(transform, q=True, ws=True, t=True)

    edges = face.getEdges()
    edge = pm.PyNode(face.node().name() + '.e[{}]'.format(str(edges[0])))
    edge_position = manipulator.getManipulatorPosition(edge)

    normal = face.getNormal(space='world')
    up = mayamath.getDirection(position, edge_position)
    matrix = mayamath.getMatrixFromVector(normal, up, location=position)
    pm.xform(transform, ws=True, m=matrix)


def orientChain(start=None, end=None, aim=None, up=None, world_up=None):
    """
    Orients the chain starting from given start and ending at given end to aim at the child joint with the
    given aim axis.

    Args:
        start (pm.nodetypes.Transform): Top parent of the chain.

        end (pm.nodetypes.Transform): The child to end search at. If none given, will return only the given start.

        aim (list): Axis to aim at

        up (list): Axis to aim at the given world direction.

        world_up (list): Axis up will try to aim at.
    """
    if not start:
        start = pm.selected()[0]

    if not end:
        end = pm.selected()[-1]

    if start == end:
        pm.error('Please select more than one transform!')

    transforms = getChain(start, end)
    first_parent = transforms[0].getParent()

    aim = convert.toVector(aim, invalid_default=[1, 0, 0])
    up = convert.toVector(up, invalid_default=[1, 0, 0])
    world_up = convert.toVector(world_up, invalid_default=[1, 0, 0])

    pm.parent(transforms, w=True)
    for i, transform in enumerate(transforms):

        if i == 0:
            if first_parent:
                pm.parent(transform, first_parent)
        else:
            pm.parent(transform, transforms[i - 1])

        if transform.hasAttr('jointOrient'):
            transform.jointOrient.set((0, 0, 0))

        if transform == transforms[-1]:
            continue

        constraint = pm.aimConstraint(transforms[i + 1], transform, aim=aim, u=up, wu=world_up, mo=False, wut='vector')
        pm.delete(constraint)


def orientChainWithUpObjects(transform_start=None, up_start=None, aim=None, up_axis=None):
    """
    Orients the given transforms by aiming the given axis to their child and the up to the respective up transform.

    Args:
        transform_start (pm.nodetypes.Transform): Start of the chain to orient.

        up_start (pm.nodetypes.Transform): Start of the chain that transforms will have their up axis aim at.

        aim (list): Axis vector to aim towards child joint.

        up_axis (list): Axis vector to aim towards the up object.
    """
    if not transform_start:
        transform_start = pm.selected()[0]

    if not up_start:
        up_start = pm.selected()[-1]

    if transform_start == up_start:
        pm.error('Please select more than one transform!')

    aim = convert.toVector(aim, invalid_default=[0, 1, 0])
    up_axis = convert.toVector(up_axis, invalid_default=[1, 0, 0])

    transforms = transform_start.getChildren(ad=True)
    uppers = up_start.getChildren(ad=True)
    transforms.append(transform_start)
    uppers.append(up_start)

    transforms.reverse()
    uppers.reverse()
    pm.parent(transforms, w=True)

    for i, (transform, up) in enumerate(zip(transforms, uppers)):
        if i != 0:
            pm.parent(transform, transforms[i - 1])

        if transform.hasAttr('jointOrient'):
            transform.jointOrient.set((0, 0, 0))

        if transform == transforms[-1]:
            continue

        constraint = pm.aimConstraint(transforms[i + 1], transform, aim=aim, u=up_axis, wuo=up, mo=False, wut='object')
        pm.delete(constraint)
