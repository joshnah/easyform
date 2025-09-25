"use client";

import React, { useEffect } from "react";

import ChangesList from "@/components/ChangesList";
import { FilePreviewCard } from "@/components/FilePreviewCard";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  detectFillEntries,
  detectPattern,
  extractContext,
  fetchContext,
  fetchFormText,
  fillForm,
  getContextData,
  previewFile,
  processFillEntries,
  provider,
  PROVIDERS,
  setProvider,
  writeContextData,
} from "@/helpers/form_helpers";
import {
  Bot,
  Check,
  CheckCircle,
  Download,
  Edit3,
  ExternalLink,
  FileCheck,
  FileText,
  Key,
  Loader2,
  Upload,
} from "lucide-react";
import { useState } from "react";
import PdfViewer from "@/components/PdfViewer";
import DocxViewer from "@/components/DocxViewer";
import ContextDataEditor from "@/components/ContextDataEditor";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import ApiKeyModal from "@/components/ApiKeyModal";

enum ProcessStep {
  AnalyzingForm = "Analyzing form structure",
  FillingFormFields = "AI filling form fields",
}

// Add TabStep enum for tab steps
enum TabStep {
  UploadForm = 1,
  SelectContext,
  ReviewContext,
  Processing,
  ReviewEdit,
  Complete,
}

export default function FormFillingAI() {
  const [currentStep, setCurrentStep] = useState<TabStep>(TabStep.UploadForm);
  const [uploadedFile, setuploadedFile] = useState<string | undefined>(
    undefined,
  );
  const [contextDir, setContextDir] = useState<DirWFilePaths | undefined>(
    undefined,
  );
  const [processingStep, setProcessingStep] = useState<ProcessStep | null>(
    null,
  );
  const [outputPath, setOutputPath] = useState<string>("");
  const [fillEntries, setFillEntries] = useState<any>(null);
  const [changedLines, setChangedLines] = useState<any>([]);
  const [isPdfUploaded, setIsPdfUploaded] = useState(true);
  const [checkboxEntries, setCheckboxEntries] = useState<any>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>(provider);
  // Context data state
  const [contextData, setContextData] = useState<Record<string, string>>({});
  const [originalContextData, setOriginalContextData] = useState<
    Record<string, string>
  >({});
  const [hasContextChanges, setHasContextChanges] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);

  const [isExtracting, setIsExtracting] = useState(false);
  const loadContextData = async () => {
    if (!contextDir) {
      return;
    }

    try {
      const contextData = await getContextData(contextDir.path);
      if (contextData) {
        setContextData(contextData);
        setOriginalContextData(contextData);
        setHasContextChanges(false);
      }
    } catch (e) {
      setContextData({});
      setOriginalContextData({});
      setHasContextChanges(false);
    }
  };
  const handleFileUpload = async () => {
    const filePath = await window.helloWorldContext.selectFile();
    if (!filePath) {
      console.error("No file selected");
      return;
    }
    setuploadedFile(filePath);
    if (filePath && filePath.toLowerCase().endsWith(".pdf")) {
      setIsPdfUploaded(true);
    }
  };

  const startNewForm = () => {
    setCurrentStep(TabStep.UploadForm);
    setuploadedFile(undefined);
    setContextDir(undefined);
    setProcessingStep(null);
    setOutputPath("");
    setFillEntries(null);
    setChangedLines([]);
    setIsPdfUploaded(false);
    setContextData({});
    setOriginalContextData({});
    setCheckboxEntries([]);
  };

  const handleChooseContextDir = async () => {
    const dir = await window.helloWorldContext.selectDirectory();
    if (dir) {
      setContextDir(dir);
    }
  };

  const updateChange = async (changeId: number, newValue: string) => {
    if (!fillEntries) {
      console.error("No fill entries available");
      return;
    }

    console.log("Updating change", changeId, "with new value:", newValue);

    // Find which fillEntry contains this change
    let globalChangeIndex = 0;
    let updatedFillEntries = [...fillEntries];
    let entryUpdated = false;

    for (
      let entryIndex = 0;
      entryIndex < updatedFillEntries.length;
      entryIndex++
    ) {
      const entry = updatedFillEntries[entryIndex];
      const originalLines = entry.lines.split("\n");
      const filledLines = entry.filled_lines.split("\n");

      for (let lineIndex = 0; lineIndex < originalLines.length; lineIndex++) {
        if (originalLines[lineIndex] !== filledLines[lineIndex]) {
          if (globalChangeIndex === changeId) {
            // Found the change to update
            console.log("Updating line", lineIndex, "in entry", entryIndex);
            console.log("Old value:", filledLines[lineIndex]);
            console.log("New value:", newValue);

            filledLines[lineIndex] = newValue;
            updatedFillEntries[entryIndex].filled_lines =
              filledLines.join("\n");
            entryUpdated = true;
            break;
          }
          globalChangeIndex++;
        }
      }
      if (entryUpdated) break;
    }

    if (entryUpdated) {
      // Update the fillEntries state
      setFillEntries(updatedFillEntries);

      try {
        // Re-fill the form with updated entries
        console.log("Re-filling form with updated entries...");
        await fillForm(
          uploadedFile!,
          updatedFillEntries,
          checkboxEntries,
          outputPath,
        );
        console.log("Form re-filled successfully");
      } catch (error) {
        console.error("Error re-filling form:", error);
      }
    } else {
      console.error("Could not find change with ID", changeId);
    }
  };

  useEffect(() => {
    if (fillEntries) {
      console.log("Fill entries updated:", fillEntries);

      const getChangedLines = () => {
        const changedLines = [];
        let index = 0;
        fillEntries.forEach((entry) => {
          const originalLines = entry.lines.split("\n");
          const filledLines = entry.filled_lines.split("\n");

          for (let i = 0; i < originalLines.length; i++) {
            if (originalLines[i] !== filledLines[i]) {
              changedLines.push({
                originalLine: originalLines[i],
                filledValue: filledLines[i],
                id: index,
              });
              index++;
            }
          }
        });

        console.log("changedLines", changedLines);
        return changedLines;
      };
      setChangedLines(getChangedLines());
    }
  }, [fillEntries]);

  const processForm = async () => {
    setCurrentStep(TabStep.Processing);
    if (!contextDir) {
      console.error("No context directory selected");
      return;
    }
    if (!uploadedFile) {
      console.error("No form chosen for processing");
      return;
    }
    if (isPdfUploaded) {
      setOutputPath(uploadedFile.replace(/\.pdf$/, "_filled.pdf"));
    } else {
      setOutputPath(uploadedFile.replace(/\.docx$/, "_filled.docx"));
    }

    try {
      setProcessingStep(ProcessStep.AnalyzingForm);
      console.log("Fetching form text");
      const formText = await fetchFormText(uploadedFile);

      console.log(
        "Form text extraction complete, length:",
        formText?.length || 0,
      );

      console.log("Fetching context from directory:", contextDir);
      const context = await fetchContext(contextDir.path);
      const keys = Object.keys(context) || [];
      console.log(
        "Context fetched successfully, keys count:",
        keys?.length || 0,
      );

      console.log("Detecting form pattern...");
      const pattern = await detectPattern(formText);
      console.log("Pattern detection complete:", pattern);

      console.log("Detecting fill entries...");
      const fillEntries = await detectFillEntries(formText, keys, pattern);
      console.log(
        "Fill entries detected:",
        fillEntries?.length || 0,
        "entries",
      );

      // console.log("Detecting checkbox entries...");
      // const checkboxEntries = await detectCheckboxEntries(formText, keys);
      // console.log("Checkbox entries detected:", checkboxEntries?.length || 0, "entries");

      console.log("Processing fill entries with context...");
      const filledEntries = await processFillEntries(
        fillEntries,
        contextDir.path,
        pattern,
      );
      setFillEntries(filledEntries);

      console.log(
        "Fill entries processed:",
        filledEntries?.length || 0,
        "entries filled",
      );

      // console.log("Processing checkbox entries with context...");
      // const filledCheckbox = await processCheckboxEntries(checkboxEntries, contextDir.path, keys);
      // setCheckboxEntries(filledCheckbox);
      // console.log("Checkbox entries processed:", filledCheckbox?.length || 0, "checkboxes filled");

      setProcessingStep(ProcessStep.FillingFormFields);
      console.log("Filling form with processed entries...");

      console.log("Output path:", `${outputPath}`);
      await fillForm(uploadedFile, filledEntries, [], outputPath);
      console.log("Form filling complete!");
      setCurrentStep(TabStep.ReviewEdit);
    } catch (error) {
      console.error("Processing failed:", error);
      setCurrentStep(TabStep.ReviewContext);
      await loadContextData();
    } finally {
      console.log("Form processing completed");
    }
  };

  const handleExtractContext = async () => {
    setIsExtracting(true);
    try {
      if (!contextDir) {
        console.error("No context directory selected");
        return;
      }
      const updatedContext = await extractContext(contextDir.path);

      setContextData(updatedContext);
      setOriginalContextData(updatedContext);
      setHasContextChanges(false);
    } finally {
      setIsExtracting(false);
    }
  };

  const progressValue = (currentStep / TabStep.Complete) * 100;

  return (
    <div className="flex h-full flex-col overflow-y-auto p-3">
      <div className="mx-auto max-w-6xl pb-8">
        <div className="mb-8">
          <h1 className="mb-2 text-3xl font-bold text-gray-900">EasyForm</h1>
          <p className="text-gray-600">
            Upload your form, provide context, and let AI fill it automatically
          </p>
        </div>
        <div className="mb-4 flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => setIsApiKeyModalOpen(true)}
            className="flex items-center space-x-2 bg-transparent"
          >
            <Key className="h-4 w-4" />
            <span>API Keys</span>
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                className="flex items-center space-x-2 bg-transparent"
              >
                <Bot className="h-4 w-4" />
                <span>Current AI provider: {selectedProvider}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>{selectedProvider}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {PROVIDERS.map((provider) => (
                <DropdownMenuItem
                  key={provider}
                  onClick={() => {
                    setSelectedProvider(provider);
                    setProvider(provider); // Update the provider in form_helpers.ts
                  }}
                  className="cursor-pointer"
                >
                  <span>{provider}</span>
                  {selectedProvider === provider && (
                    <Check className="ml-auto h-4 w-4 text-green-600" />
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">
              Step {currentStep} of {TabStep.Complete}
            </span>
            <span className="text-sm text-gray-500">
              {Math.round(progressValue)}% Complete
            </span>
          </div>
          <Progress value={progressValue} className="h-2" />
        </div>

        <Tabs value={currentStep.toString()} className="w-full">
          <TabsList className="mb-8 grid w-full grid-cols-5">
            <TabsTrigger
              value={TabStep.UploadForm.toString()}
              disabled={currentStep < TabStep.UploadForm}
            >
              <Upload className="mr-2 h-4 w-4" />
              Upload Form
            </TabsTrigger>
            <TabsTrigger
              value={TabStep.SelectContext.toString()}
              disabled={currentStep < TabStep.SelectContext}
            >
              <FileText className="mr-2 h-4 w-4" />
              Select Context
            </TabsTrigger>
            <TabsTrigger
              value={TabStep.ReviewContext.toString()}
              disabled={currentStep < TabStep.SelectContext}
            >
              <FileText className="mr-2 h-4 w-4" />
              Review Context
            </TabsTrigger>
            <TabsTrigger
              value={TabStep.ReviewEdit.toString()}
              disabled={currentStep < TabStep.ReviewEdit}
            >
              <CheckCircle className="mr-2 h-4 w-4" />
              Review & Edit
            </TabsTrigger>
            <TabsTrigger
              value={TabStep.Complete.toString()}
              disabled={currentStep < TabStep.Complete}
            >
              <FileCheck className="mr-2 h-4 w-4" />
              Complete
            </TabsTrigger>
          </TabsList>

          {/* Upload Form */}
          <TabsContent
            value={TabStep.UploadForm.toString()}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <CardTitle>Upload PDF Form</CardTitle>
                <CardDescription>
                  Select the PDF form you want to fill automatically
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center transition-colors hover:border-gray-400">
                  <Button
                    onClick={handleFileUpload}
                    className="flex h-full w-full cursor-pointer flex-col items-center justify-center border-none bg-transparent hover:bg-gray-50"
                  >
                    <Upload className="mb-4 h-12 w-12 text-gray-400" />
                    <span className="text-lg font-medium text-gray-700">
                      Click to upload PDF or DOCX form
                    </span>
                    <p className="mt-1 text-sm text-gray-500">
                      Supports PDF files up to 10MB
                    </p>
                  </Button>
                </div>

                {uploadedFile && <FilePreviewCard path={uploadedFile} />}

                <div className="flex justify-end">
                  <Button
                    onClick={() => setCurrentStep(TabStep.SelectContext)}
                    disabled={!uploadedFile}
                  >
                    Next: Select Context
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Select Context */}
          <TabsContent
            value={TabStep.SelectContext.toString()}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <CardTitle>Choose context folder</CardTitle>
                <CardDescription>
                  Provide context folder to help AI understand how to fill the
                  form
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center transition-colors hover:border-gray-400">
                  <Button
                    onClick={handleChooseContextDir}
                    className="flex h-full w-full cursor-pointer flex-col items-center justify-center border-none bg-transparent p-8 hover:bg-gray-50"
                  >
                    <Upload className="mb-4 h-12 w-12 text-gray-400" />
                    <span className="text-lg font-medium text-gray-700">
                      Click to choose context folder
                    </span>
                  </Button>
                </div>

                {contextDir &&
                  contextDir.filePaths.map((filePath, id) => (
                    <FilePreviewCard key={id} path={filePath} />
                  ))}

                <div className="flex justify-between">
                  <Button
                    variant="outline"
                    onClick={() => setCurrentStep(TabStep.UploadForm)}
                  >
                    Back
                  </Button>
                  <Button
                    onClick={() => {
                      loadContextData();
                      setCurrentStep(TabStep.ReviewContext);
                    }}
                  >
                    Review context
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          {/* Review Context */}
          <TabsContent
            value={TabStep.ReviewContext.toString()}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Review Context Data</CardTitle>
                    <CardDescription>
                      Review and modify the extracted context data from your
                      files. This data will be used to fill the form.
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    onClick={handleExtractContext}
                    disabled={isExtracting}
                    className="flex items-center space-x-2 bg-transparent"
                  >
                    {isExtracting ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>Extracting...</span>
                      </>
                    ) : (
                      <>
                        <Download className="h-4 w-4" />
                        <span>Extract Context</span>
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <svg
                        className="mt-0.5 h-5 w-5 text-blue-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-blue-900">
                        Context Data Source
                      </h4>
                      <p className="mt-1 text-sm text-blue-700">
                        This data was extracted from your uploaded context files
                        and compiled into a structured format. You can edit any
                        values or add new fields as needed.
                      </p>
                    </div>
                  </div>
                </div>

                <ContextDataEditor
                  data={contextData}
                  onChange={(newData) => {
                    setContextData(newData);
                    setHasContextChanges(
                      JSON.stringify(newData) !==
                        JSON.stringify(originalContextData),
                    );
                  }}
                />

                {hasContextChanges && (
                  <div className="flex justify-center">
                    <Button
                      variant="outline"
                      className="border-yellow-300 bg-yellow-50 text-yellow-800 hover:bg-yellow-100"
                      onClick={() => {
                        if (!contextDir) {
                          console.error("No context directory selected");
                          return;
                        }
                        console.log("Saving context changes:", contextData);
                        writeContextData(contextDir.path, contextData);
                        setOriginalContextData(contextData);
                        setHasContextChanges(false);
                      }}
                    >
                      <Check className="mr-2 h-4 w-4" />
                      Save Context Changes
                    </Button>
                  </div>
                )}

                <div className="flex justify-between">
                  <Button variant="outline" onClick={() => setCurrentStep(2)}>
                    Back
                  </Button>
                  <Button onClick={processForm}>Process Form</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Review & Edit */}
          <TabsContent
            value={TabStep.ReviewEdit.toString()}
            className="space-y-6"
          >
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Left Panel: PDF Preview */}
              <Card>
                <CardHeader>
                  <CardTitle>Form Preview</CardTitle>
                  <CardDescription>
                    Highlighted fields show detected form elements
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isPdfUploaded && (
                    <PdfViewer pdfPath={outputPath}></PdfViewer>
                  )}
                  {!isPdfUploaded && (
                    <DocxViewer filePath={outputPath}></DocxViewer>
                  )}
                </CardContent>
              </Card>

              {/* Right Panel: Field Status */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Edit3 className="h-5 w-5" />
                    <span>Changes List</span>
                  </CardTitle>
                  <CardDescription>Review AI-generated changes</CardDescription>
                </CardHeader>
                <CardContent className="max-h-[600px] space-y-4 overflow-y-auto">
                  <ChangesList
                    changes={changedLines}
                    onUpdateChange={updateChange}
                  />
                </CardContent>
              </Card>
            </div>

            <div className="flex items-center justify-between">
              <Button
                variant="outline"
                onClick={() => setCurrentStep(TabStep.SelectContext)}
              >
                Back
              </Button>
              <Button
                className="bg-green-600 hover:bg-green-700"
                onClick={() => setCurrentStep(TabStep.Complete)}
              >
                <Check className="mr-2 h-4 w-4" />
                Finish
              </Button>
            </div>
          </TabsContent>

          {/* Complete */}
          <TabsContent
            value={TabStep.Complete.toString()}
            className="space-y-6"
          >
            <div className="py-8 text-center">
              <div className="mb-6rounded-full mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                <Check className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="mb-2 text-2xl font-bold text-gray-900">
                Form Successfully Completed!
              </h2>
              <p className="mb-8 text-gray-600">
                Your form has been filled and is ready for download.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Original File */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <FileText className="h-5 w-5" />
                    <span>Original File</span>
                  </CardTitle>
                  <CardDescription>
                    The original form you uploaded
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {uploadedFile && (
                    <div className="flex items-center space-x-4 rounded-lg border bg-gray-50 p-4">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900">
                          {uploadedFile}
                        </h3>
                        <p className="text-sm text-gray-500">
                          {isPdfUploaded ? "PDF" : "DOCX"}
                        </p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Filled File */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <FileCheck className="h-5 w-5 text-green-600" />
                    <span>Filled File</span>
                  </CardTitle>
                  <CardDescription>
                    The completed form with AI-filled data
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center space-x-4 rounded-lg border border-green-200 bg-green-50 p-4">
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">
                        {outputPath}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {isPdfUploaded ? "PDF" : "DOCX"}
                      </p>
                    </div>
                  </div>
                  {/* Preview Button takes all width */}
                  <div className="mt-4 flex justify-end">
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => previewFile(outputPath)}
                    >
                      <ExternalLink className="mr-2" />
                      Preview
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Summary Stats */}
            {/* <Card>
              <CardHeader>
                <CardTitle>Processing Summary</CardTitle>
                <CardDescription>Overview of the form filling process</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">{changes.length}</div>
                    <div className="text-sm text-gray-600">Fields Filled</div>
                  </div>
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">
                      {changes.filter((c) => c.confidence === "high").length}
                    </div>
                    <div className="text-sm text-gray-600">High Confidence</div>
                  </div>
                  <div className="text-center p-4 bg-yellow-50 rounded-lg">
                    <div className="text-2xl font-bold text-yellow-600">
                      {changes.filter((c) => c.confidence === "medium").length}
                    </div>
                    <div className="text-sm text-gray-600">Medium Confidence</div>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded-lg">
                    <div className="text-2xl font-bold text-red-600">
                      {changes.filter((c) => c.confidence === "low").length}
                    </div>
                    <div className="text-sm text-gray-600">Low Confidence</div>
                  </div>
                </div>
              </CardContent>
            </Card> */}

            {/* Actions */}
            <div className="flex items-center justify-between">
              <Button variant="outline" onClick={startNewForm}>
                Start New Form
              </Button>
              <div className="flex space-x-2">
                <Button>Share Results</Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Processing Step */}
        {currentStep === TabStep.Processing && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Processing Your Form</CardTitle>
                <CardDescription>
                  AI is analyzing your form and context files to fill the form
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="mb-6 h-16 w-16 animate-spin rounded-full border-b-2 border-blue-600"></div>
                  <h3 className="mb-2 text-lg font-medium text-gray-900">
                    Processing in progress...
                  </h3>
                  <p className="mb-6 text-center text-gray-600">
                    {processingStep}
                  </p>

                  <div className="w-full max-w-md space-y-3">
                    <div className="flex justify-between text-sm">
                      <span>Analyzing form structure</span>
                      <span className="text-green-600">✓</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>AI filling form fields</span>
                      <span
                        className={
                          processingStep === ProcessStep.FillingFormFields
                            ? "text-green-600"
                            : "text-gray-400"
                        }
                      >
                        {processingStep === ProcessStep.FillingFormFields
                          ? "✓"
                          : "⏳"}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        {/* API Key Modal */}
        <ApiKeyModal
          isOpen={isApiKeyModalOpen}
          onClose={() => setIsApiKeyModalOpen(false)}
          selectedProvider={selectedProvider}
          onProviderChange={setSelectedProvider}
        />
      </div>
    </div>
  );
}
