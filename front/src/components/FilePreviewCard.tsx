import React from 'react';
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { previewFile } from '@/helpers/form_helpers';

export function FilePreviewCard({ path }: { path: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 p-4">
      <div className="flex-1">
        <h3 className="font-medium text-gray-900">
          {path.split('/').pop()}
        </h3>
        <p className="text-sm text-gray-500">
          {path}
        </p>
        <Badge
          variant="secondary"
          className="mt-1 bg-green-100 text-green-800"
        >
          Ready to process
        </Badge>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={() => previewFile(path)}
        className="bg-green-100 text-green-800 hover:bg-green-200 hover:text-green-800 border-green-500"
      >
        Preview
      </Button>
    </div>
  )
}
