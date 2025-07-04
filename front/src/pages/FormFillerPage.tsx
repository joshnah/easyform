"use client";

import React from "react";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  Save,
} from "lucide-react";
import ReviewPdf from "@/components/Review";

// Mock data for form fields
const mockFormFields = [
  {
    id: 1,
    name: "Full Name",
    value: "John Smith",
    status: "filled",
    confidence: "high",
  },
  {
    id: 2,
    name: "Email Address",
    value: "john.smith@email.com",
    status: "filled",
    confidence: "high",
  },
  {
    id: 3,
    name: "Phone Number",
    value: "(555) 123-4567",
    status: "filled",
    confidence: "medium",
  },
  {
    id: 4,
    name: "Date of Birth",
    value: "",
    status: "empty",
    confidence: "low",
  },
  {
    id: 5,
    name: "Address Line 1",
    value: "123 Main Street",
    status: "filled",
    confidence: "high",
  },
  {
    id: 6,
    name: "Address Line 2",
    value: "",
    status: "empty",
    confidence: "low",
  },
  {
    id: 7,
    name: "City",
    value: "New York",
    status: "filled",
    confidence: "medium",
  },
  { id: 8, name: "State", value: "NY", status: "filled", confidence: "high" },
  {
    id: 9,
    name: "ZIP Code",
    value: "10001",
    status: "filled",
    confidence: "medium",
  },
  {
    id: 10,
    name: "Social Security Number",
    value: "",
    status: "empty",
    confidence: "low",
  },
];

export default function FormFillingAI() {
  const [currentStep, setCurrentStep] = useState(1);
  const [uploadedPDF, setUploadedPDF] = useState<File | null>(null);
  const [contextFiles, setContextFiles] = useState<File[]>([]);
  const [formFields, setFormFields] = useState(mockFormFields);

  const handlePDFUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === "application/pdf") {
      setUploadedPDF(file);
    }
  };

  const handleContextUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setContextFiles((prev) => [...prev, ...files]);
  };

  const removeContextFile = (index: number) => {
    setContextFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const updateFieldValue = (fieldId: number, value: string) => {
    setFormFields((prev) =>
      prev.map((field) =>
        field.id === fieldId
          ? { ...field, value, status: value ? "filled" : "empty" }
          : field,
      ),
    );
  };

  const getStatusIcon = (status: string, confidence: string) => {
    if (status === "filled") {
      return confidence === "medium" ? (
        <AlertCircle className="h-4 w-4 text-yellow-500" />
      ) : (
        <CheckCircle className="h-4 w-4 text-green-500" />
      );
    }
    return <XCircle className="h-4 w-4 text-red-500" />;
  };

  const getStatusBadge = (status: string, confidence: string) => {
    if (status === "filled") {
      return confidence === "medium" ? (
        <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
          Low Confidence
        </Badge>
      ) : (
        <Badge variant="secondary" className="bg-green-100 text-green-800">
          Filled
        </Badge>
      );
    }
    return (
      <Badge variant="secondary" className="bg-red-100 text-red-800">
        Not Filled
      </Badge>
    );
  };

  const progressValue = (currentStep / 3) * 100;

  return (
    <div className="flex h-full flex-col overflow-y-auto p-3">
      <div className="mx-auto max-w-6xl pb-8">
        <div className="mb-8">
          <h1 className="mb-2 text-3xl font-bold text-gray-900">
            Form Filling AI Tool
          </h1>
          <p className="text-gray-600">
            Upload your form, provide context, and let AI fill it automatically
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">
              Step {currentStep} of 3
            </span>
            <span className="text-sm text-gray-500">
              {Math.round(progressValue)}% Complete
            </span>
          </div>
          <Progress value={progressValue} className="h-2" />
        </div>

        <Tabs value={currentStep.toString()} className="w-full">
          <TabsList className="mb-8 grid w-full grid-cols-3">
            <TabsTrigger value="1" disabled={currentStep < 1}>
              <Upload className="mr-2 h-4 w-4" />
              Upload Form
            </TabsTrigger>
            <TabsTrigger value="2" disabled={currentStep < 2}>
              <FileText className="mr-2 h-4 w-4" />
              Select Context
            </TabsTrigger>
            <TabsTrigger value="3" disabled={currentStep < 3}>
              <CheckCircle className="mr-2 h-4 w-4" />
              Review & Edit
            </TabsTrigger>
          </TabsList>

          {/* Step 1: Upload Form */}
          <TabsContent value="1" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Upload PDF Form</CardTitle>
                <CardDescription>
                  Select the PDF form you want to fill automatically
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center transition-colors hover:border-gray-400">
                  <Label
                    htmlFor="pdf-upload"
                    className="flex cursor-pointer flex-col items-center"
                  >
                    <Upload className="mb-4 h-12 w-12 text-gray-400" />
                    <span className="text-lg font-medium text-gray-700">
                      Click to upload PDF form
                    </span>
                    <p className="mt-1 text-sm text-gray-500">
                      Supports PDF files up to 10MB
                    </p>
                  </Label>
                  <Input
                    id="pdf-upload"
                    type="file"
                    accept=".pdf"
                    onChange={handlePDFUpload}
                    className="hidden"
                  />
                </div>

                {uploadedPDF && (
                  <div className="flex items-center space-x-4 rounded-lg border border-green-200 bg-green-50 p-4">
                    <div className="flex-shrink-0">
                      <img
                        src="/placeholder.svg?height=80&width=60"
                        alt="PDF thumbnail"
                        className="h-20 w-15 rounded border object-cover"
                      />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">
                        {uploadedPDF.name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {(uploadedPDF.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                      <Badge
                        variant="secondary"
                        className="mt-1 bg-green-100 text-green-800"
                      >
                        Ready to process
                      </Badge>
                    </div>
                  </div>
                )}

                <div className="flex justify-end">
                  <Button
                    onClick={() => setCurrentStep(2)}
                    disabled={!uploadedPDF}
                  >
                    Next: Select Context
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Step 2: Select Context */}
          <TabsContent value="2" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Upload Context Files</CardTitle>
                <CardDescription>
                  Provide context files to help AI understand how to fill the
                  form
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border-2 border-dashed border-gray-300 p-6 text-center transition-colors hover:border-gray-400">
                  <FileText className="mx-auto mb-3 h-10 w-10 text-gray-400" />
                  <Label
                    htmlFor="context-upload"
                    className="flex cursor-pointer flex-col items-center"
                  >
                    <span className="font-medium text-gray-700">
                      Upload context files
                    </span>
                    <p className="mt-1 text-sm text-gray-500">
                      Text, Markdown, JSON files
                    </p>
                  </Label>
                  <Input
                    id="context-upload"
                    type="file"
                    multiple
                    accept=".txt,.md,.json"
                    onChange={handleContextUpload}
                    className="hidden"
                  />
                </div>

                {contextFiles.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="font-medium text-gray-900">
                      Uploaded Context Files:
                    </h3>
                    {contextFiles.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 p-3"
                      >
                        <div className="flex items-center space-x-3">
                          <FileText className="h-5 w-5 text-blue-500" />
                          <div>
                            <p className="font-medium text-gray-900">
                              {file.name}
                            </p>
                            <p className="text-sm text-gray-500">
                              {(file.size / 1024).toFixed(1)} KB
                            </p>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeContextFile(index)}
                          className="text-red-500 hover:text-red-700"
                        >
                          Remove
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex justify-between">
                  <Button variant="outline" onClick={() => setCurrentStep(1)}>
                    Back
                  </Button>
                  <Button onClick={() => setCurrentStep(3)}>
                    Next: Review & Edit
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Step 3: Review & Edit */}
          <TabsContent value="3" className="space-y-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Left Panel: PDF Preview */}
              <Card className="h-fit">
                <CardHeader>
                  <CardTitle>Form Preview</CardTitle>
                  <CardDescription>
                    Highlighted fields show detected form elements
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ReviewPdf></ReviewPdf>
                </CardContent>
              </Card>

              {/* Right Panel: Field Status */}
              <Card>
                <CardHeader>
                  <CardTitle>Field Status</CardTitle>
                  <CardDescription>
                    Review and edit auto-filled form fields
                  </CardDescription>
                </CardHeader>
                <CardContent className="max-h-[600px] space-y-4 overflow-y-auto">
                  {formFields.map((field) => (
                    <div
                      key={field.id}
                      className="space-y-3 rounded-lg border p-4"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(field.status, field.confidence)}
                          <span className="font-medium text-gray-900">
                            {field.name}
                          </span>
                        </div>
                        {getStatusBadge(field.status, field.confidence)}
                      </div>

                      {field.status === "filled" ? (
                        <div className="space-y-2">
                          <p className="text-sm text-gray-600">
                            Auto-filled value:
                          </p>
                          <Input
                            value={field.value}
                            onChange={(e) =>
                              updateFieldValue(field.id, e.target.value)
                            }
                            className="bg-gray-50"
                          />
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <p className="text-sm text-gray-600">
                            Please fill manually:
                          </p>
                          <Input
                            placeholder={`Enter ${field.name.toLowerCase()}`}
                            value={field.value}
                            onChange={(e) =>
                              updateFieldValue(field.id, e.target.value)
                            }
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <div className="flex items-center justify-between">
              <Button variant="outline" onClick={() => setCurrentStep(2)}>
                Back
              </Button>
              <Button className="bg-green-600 hover:bg-green-700">
                <Save className="mr-2 h-4 w-4" />
                Save Form
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
