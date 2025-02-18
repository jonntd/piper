//  Copyright (c) 2021 Christian Corsica. All Rights Reserved.

#include "PiperMath.h"
#include "util.h"

#include <maya/MFnMatrixAttribute.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnCompoundAttribute.h>
#include <maya/MGlobal.h>

#include <iso646.h>


// Piper Multiply
MTypeId PiperMultiply::type_ID(0x00137146);
MString PiperMultiply::node_name("piperMultiply");
MObject PiperMultiply::weight;
MObject PiperMultiply::main_term;
MObject PiperMultiply::input;
MObject PiperMultiply::outputX;
MObject PiperMultiply::outputY;
MObject PiperMultiply::outputZ;
MObject PiperMultiply::output;


void* PiperMultiply::creator()
{
    return new PiperMultiply();
}


MStatus PiperMultiply::initialize()
{
    MFnNumericAttribute numeric_fn;
    MFnCompoundAttribute compound_fn;

    weight = numeric_fn.create("weight", "wgt", MFnNumericData::kDouble, 1);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    numeric_fn.setMin(0.0);
    numeric_fn.setMax(1.0);
    addAttribute(weight);

    main_term = numeric_fn.create("mainTerm", "mtr", MFnNumericData::kDouble, 1);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(main_term);

    input = numeric_fn.create("input", "inp", MFnNumericData::kDouble, 1.0);
    numeric_fn.setArray(true);
    numeric_fn.setUsesArrayDataBuilder(true);
    numeric_fn.setKeyable(true);
    numeric_fn.setStorable(true);
    numeric_fn.setWritable(true);
    addAttribute(input);

    // OUTPUT
    outputX = numeric_fn.create("outputX", "oux", MFnNumericData::kDouble, 1.0);
    numeric_fn.setStorable(false);
    numeric_fn.setKeyable(false);
    numeric_fn.setWritable(false);
    addAttribute(outputX);

    outputY = numeric_fn.create("outputY", "ouy", MFnNumericData::kDouble, 1.0);
    numeric_fn.setStorable(false);
    numeric_fn.setKeyable(false);
    numeric_fn.setWritable(false);
    addAttribute(outputY);

    outputZ = numeric_fn.create("outputZ", "ouz", MFnNumericData::kDouble, 1.0);
    numeric_fn.setStorable(false);
    numeric_fn.setKeyable(false);
    numeric_fn.setWritable(false);
    addAttribute(outputZ);

    output = compound_fn.create("output", "out");
    compound_fn.addChild(outputX);
    compound_fn.addChild(outputY);
    compound_fn.addChild(outputZ);
    compound_fn.setStorable(false);
    compound_fn.setKeyable(false);
    compound_fn.setWritable(false);
    addAttribute(output);

    attributeAffects(weight, output);
    attributeAffects(main_term, output);
    attributeAffects(input, output);

    return MS::kSuccess;
}


MStatus PiperMultiply::compute(const MPlug& plug, MDataBlock& data)
{
    if (plug == output or plug == outputX or plug == outputY or plug == outputZ)
    {
        double weight_value = data.inputValue(weight).asDouble();
        double main_value = data.inputValue(main_term).asDouble();

        if (weight_value == 0.0)
        {
            data.outputValue(output).set(main_value, main_value, main_value);
            data.outputValue(output).setClean();
        }
        else
        {

            MArrayDataHandle input_data = data.inputArrayValue(input);
            unsigned int input_length = input_data.elementCount();
            double result = main_value;

            for (unsigned int i = 0; i < input_length; i++)
            {
                MDataHandle input_value = input_data.inputValue();
                result *= input_value.asDouble();
                input_data.next();
            }

            result = lerp(main_value, result, weight_value);
            data.outputValue(output).set(result, result, result);
            data.outputValue(output).setClean();

        }
    }

    return MS::kSuccess;
}


// Piper Reciprocal
MTypeId PiperReciprocal::type_ID(0x00137148);
MString PiperReciprocal::node_name("piperReciprocal");
MObject PiperReciprocal::input;
MObject PiperReciprocal::output;


void* PiperReciprocal::creator()
{
    return new PiperReciprocal();
}


MStatus PiperReciprocal::initialize()
{
    MFnNumericAttribute numeric_fn;

    input = numeric_fn.create("input", "inp", MFnNumericData::kDouble, 1);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(input);

    output = numeric_fn.create("output", "out", MFnNumericData::kDouble, 1.0);
    numeric_fn.setStorable(false);
    numeric_fn.setKeyable(false);
    numeric_fn.setWritable(false);
    addAttribute(output);

    attributeAffects(input, output);

    return MS::kSuccess;
}


MStatus PiperReciprocal::compute(const MPlug &plug, MDataBlock &data)
{
    if (plug == output)
    {
        double input_value = data.inputValue(input).asDouble();
        double output_value = reciprocal(input_value);
        data.outputValue(output).set(output_value);
        data.outputValue(output).setClean();
    }

    return MS::kSuccess;

}


// Piper One Minus
MTypeId PiperOneMinus::type_ID(0x00137149);
MString PiperOneMinus::node_name("piperOneMinus");
MObject PiperOneMinus::input;
MObject PiperOneMinus::output;


void* PiperOneMinus::creator()
{
    return new PiperOneMinus();
}


MStatus PiperOneMinus::initialize()
{
    MFnNumericAttribute numeric_fn;

    input = numeric_fn.create("input", "inp", MFnNumericData::kDouble, 0);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(input);

    output = numeric_fn.create("output", "out", MFnNumericData::kDouble, 0);
    numeric_fn.setStorable(false);
    numeric_fn.setKeyable(false);
    numeric_fn.setWritable(false);
    addAttribute(output);

    attributeAffects(input, output);

    return MS::kSuccess;
}


MStatus PiperOneMinus::compute(const MPlug &plug, MDataBlock &data)
{
    if (plug == output)
    {
        double input_value = data.inputValue(input).asDouble();
        double output_value = (input_value * -1.0) + signOf(input_value);
        data.outputValue(output).set(output_value);
        data.outputValue(output).setClean();
    }

    return MS::kSuccess;

}

// Piper Orient Matrix
MTypeId PiperOrientMatrix::type_ID(0x0013714A);
MString PiperOrientMatrix::node_name("piperOrientMatrix");
MObject PiperOrientMatrix::use_orient;
MObject PiperOrientMatrix::position_matrix;
MObject PiperOrientMatrix::orient_matrix;
MObject PiperOrientMatrix::output;


void* PiperOrientMatrix::creator()
{
    return new PiperOrientMatrix();
}


MStatus PiperOrientMatrix::initialize()
{
    MFnMatrixAttribute matrix_fn;
    MFnNumericAttribute numeric_fn;

    use_orient = numeric_fn.create("useOrient", "uso", MFnNumericData::kBoolean, 1.0);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    numeric_fn.setWritable(true);
    addAttribute(use_orient);

    position_matrix = matrix_fn.create("positionMatrix", "pom");
    matrix_fn.setStorable(true);
    matrix_fn.setKeyable(true);
    addAttribute(position_matrix);

    orient_matrix = matrix_fn.create("orientMatrix", "oim");
    matrix_fn.setStorable(true);
    matrix_fn.setKeyable(true);
    addAttribute(orient_matrix);

    output = matrix_fn.create("output", "out");
    matrix_fn.setStorable(false);
    matrix_fn.setKeyable(false);
    matrix_fn.setWritable(false);
    addAttribute(output);

    attributeAffects(use_orient, output);
    attributeAffects(position_matrix, output);
    attributeAffects(orient_matrix, output);

    return MS::kSuccess;
}


MStatus PiperOrientMatrix::compute(const MPlug &plug, MDataBlock &data)
{
    if (plug == output)
    {
        bool use_orient_value = data.inputValue(use_orient).asBool();
        MMatrix orient_matrix_value = data.inputValue(orient_matrix).asMatrix();

        if (use_orient_value)
        {
            MMatrix position_matrix_value = data.inputValue(position_matrix).asMatrix();


            MTransformationMatrix position_transform = MTransformationMatrix(position_matrix_value);
            MTransformationMatrix orient_transform = MTransformationMatrix(orient_matrix_value);
            MTransformationMatrix output_transform;

            double x, y, z, w;
            orient_transform.getRotationQuaternion(x, y, z, w);
            output_transform.setRotationQuaternion(x, y, z, w);

            double scale[3];
            position_transform.getScale(scale, MSpace::kWorld);
            output_transform.setScale(scale, MSpace::kWorld);
            output_transform.setTranslation(position_transform.getTranslation(MSpace::kWorld), MSpace::kWorld);

            data.outputValue(output).set(output_transform.asMatrix());
        }
        else
        {
            data.outputValue(output).set(orient_matrix_value);
        }

        data.outputValue(output).setClean();

    }

    return MS::kSuccess;
}


// Piper Blend Axis
MTypeId PiperBlendAxis::type_ID(0x0013714C);
MString PiperBlendAxis::node_name("piperBlendAxis");
MObject PiperBlendAxis::weight;
MObject PiperBlendAxis::axis1;
MObject PiperBlendAxis::axis1X;
MObject PiperBlendAxis::axis1Y;
MObject PiperBlendAxis::axis1Z;
MObject PiperBlendAxis::axis2;
MObject PiperBlendAxis::axis2X;
MObject PiperBlendAxis::axis2Y;
MObject PiperBlendAxis::axis2Z;
MObject PiperBlendAxis::output;
MObject PiperBlendAxis::outputX;
MObject PiperBlendAxis::outputY;
MObject PiperBlendAxis::outputZ;


void* PiperBlendAxis::creator()
{
    return new PiperBlendAxis();
}


MStatus PiperBlendAxis::initialize()
{
    MFnMatrixAttribute matrix_fn;
    MFnNumericAttribute numeric_fn;
    MFnCompoundAttribute compound_fn;

    weight = numeric_fn.create("weight", "weg", MFnNumericData::kDouble, 1);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    numeric_fn.setMin(0);
    numeric_fn.setMax(1);
    addAttribute(weight);

    axis1X = numeric_fn.create("axis1X", "a1x", MFnNumericData::kDouble, 0.0);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(axis1X);

    axis1Y = numeric_fn.create("axis1Y", "a1y", MFnNumericData::kDouble, 0.0);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(axis1Y);

    axis1Z = numeric_fn.create("axis1Z", "a1z", MFnNumericData::kDouble, 0.0);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(axis1Z);

    axis1 = compound_fn.create("axis1", "ax1");
    compound_fn.addChild(axis1X);
    compound_fn.addChild(axis1Y);
    compound_fn.addChild(axis1Z);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(axis1);

    axis2X = numeric_fn.create("axis2X", "a2x", MFnNumericData::kDouble, 0.0);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(axis2X);

    axis2Y = numeric_fn.create("axis2Y", "a2y", MFnNumericData::kDouble, 0.0);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(axis2Y);

    axis2Z = numeric_fn.create("axis2Z", "a2z", MFnNumericData::kDouble, 0.0);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(axis2Z);

    axis2 = compound_fn.create("axis2", "ax2");
    compound_fn.addChild(axis2X);
    compound_fn.addChild(axis2Y);
    compound_fn.addChild(axis2Z);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(axis2);

    outputX = numeric_fn.create("outputX", "oux", MFnNumericData::kDouble, 0.0);
    numeric_fn.setStorable(false);
    numeric_fn.setKeyable(false);
    numeric_fn.setWritable(false);
    addAttribute(outputX);

    outputY = numeric_fn.create("outputY", "ouy", MFnNumericData::kDouble, 0.0);
    numeric_fn.setStorable(false);
    numeric_fn.setKeyable(false);
    numeric_fn.setWritable(false);
    addAttribute(outputY);

    outputZ = numeric_fn.create("outputZ", "ouz", MFnNumericData::kDouble, 0.0);
    numeric_fn.setStorable(false);
    numeric_fn.setKeyable(false);
    numeric_fn.setWritable(false);
    addAttribute(outputZ);

    output = compound_fn.create("output", "out");
    compound_fn.addChild(outputX);
    compound_fn.addChild(outputY);
    compound_fn.addChild(outputZ);
    compound_fn.setStorable(false);
    compound_fn.setKeyable(false);
    compound_fn.setWritable(false);
    addAttribute(output);

    attributeAffects(weight, output);
    attributeAffects(axis1, output);
    attributeAffects(axis2, output);

    return MS::kSuccess;
}


MStatus PiperBlendAxis::compute(const MPlug &plug, MDataBlock &data)
{
    if (plug == output or plug == outputX or plug == outputY or plug == outputZ)
    {
        double weight_value = data.inputValue(weight).asDouble();
        MVector first_axis_value = data.inputValue(axis1).asVector();
        MVector second_axis_value = data.inputValue(axis2).asVector();

        MVector output_value;
        output_value.x = lerp(first_axis_value.x, second_axis_value.x, weight_value);
        output_value.y = lerp(first_axis_value.y, second_axis_value.y, weight_value);
        output_value.z = lerp(first_axis_value.z, second_axis_value.z, weight_value);

        data.outputValue(output).set(output_value);
        data.outputValue(output).setClean();
    }

    return MS::kSuccess;
}


// Piper Safe Divide
MTypeId PiperSafeDivide::type_ID(0x0013714D);
MString PiperSafeDivide::node_name("piperSafeDivide");
MObject PiperSafeDivide::input1;
MObject PiperSafeDivide::input2;
MObject PiperSafeDivide::output;


void* PiperSafeDivide::creator()
{
    return new PiperSafeDivide();
}


MStatus PiperSafeDivide::initialize()
{
    MFnNumericAttribute numeric_fn;

    input1 = numeric_fn.create("input1", "in1", MFnNumericData::kDouble, 1);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(input1);

    input2 = numeric_fn.create("input2", "in2", MFnNumericData::kDouble, 1);
    numeric_fn.setStorable(true);
    numeric_fn.setKeyable(true);
    addAttribute(input2);

    output = numeric_fn.create("output", "out", MFnNumericData::kDouble, 0);
    numeric_fn.setStorable(false);
    numeric_fn.setKeyable(false);
    numeric_fn.setWritable(false);
    addAttribute(output);

    attributeAffects(input1, output);
    attributeAffects(input2, output);

    return MS::kSuccess;
}


MStatus PiperSafeDivide::compute(const MPlug &plug, MDataBlock &data)
{
    if (plug == output)
    {
        double input1_value = data.inputValue(input1).asDouble();
        double input2_value = data.inputValue(input2).asDouble();
        double output_value = safeDivide(input1_value, input2_value);
        data.outputValue(output).set(output_value);
        data.outputValue(output).setClean();
    }

    return MS::kSuccess;
}