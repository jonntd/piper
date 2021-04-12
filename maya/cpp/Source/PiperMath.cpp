//  Copyright (c) 2021 Christian Corsica. All Rights Reserved.

#include "PiperMath.h"

#include <maya/MFnNumericAttribute.h>
#include <maya/MFnCompoundAttribute.h>
#include <maya/MGlobal.h>

#include <iso646.h>


MTypeId PiperMultiply::type_ID(0x00137146);
MString PiperMultiply::node_name("piperMultiply");
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

    outputY = numeric_fn.create("outputT", "ouy", MFnNumericData::kDouble, 1.0);
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

    attributeAffects(input, output);

    return MS::kSuccess;
}


MStatus PiperMultiply::compute(const MPlug& plug, MDataBlock& data)
{
    if (plug == output or plug == outputX or plug == outputY or plug == outputZ)
    {

        MArrayDataHandle input_data = data.inputArrayValue(input);
        unsigned int input_length = input_data.elementCount();
        double result = 1;

        for (unsigned int i = 0; i < input_length; i++)
        {
            MDataHandle input_value = input_data.inputValue();
            result *= input_value.asDouble();
            input_data.next();
        }

        data.outputValue(output).set(result, result, result);
        data.outputValue(output).setClean();

    }

    return MS::kSuccess;
}