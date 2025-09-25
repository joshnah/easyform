"use client"
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Edit3, Plus, Search, Trash2 } from "lucide-react";
import React, { useState } from "react";

interface ContextDataEditorProps {
  data: Record<string, string>
  onChange: (data: Record<string, string>) => void
}

export default function ContextDataEditor({ data, onChange }: ContextDataEditorProps) {
  const [editingField, setEditingField] = useState<string | null>(null)
  const [newFieldKey, setNewFieldKey] = useState("")
  const [newFieldValue, setNewFieldValue] = useState("")
  const [isAddingField, setIsAddingField] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")

  const updateValue = (key: string, value: string) => {
    const newData = { ...data, [key]: value }
    onChange(newData)
  }

  const deleteField = (key: string) => {
    const newData = { ...data }
    delete newData[key]
    onChange(newData)
  }

  const addField = () => {
    if (newFieldKey.trim() && newFieldValue.trim()) {
      const newData = { ...data, [newFieldKey.trim()]: newFieldValue.trim() }
      onChange(newData)
      setNewFieldKey("")
      setNewFieldValue("")
      setIsAddingField(false)
    }
  }

  const formatFieldName = (key: string) => {
    return key
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  }

  const filteredData = Object.entries(data).filter(
    ([key, value]) =>
      key.toLowerCase().includes(searchTerm.toLowerCase()) || value.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const renderField = (key: string, value: string) => {
    const isEditing = editingField === key

    return (
      <div key={key} className="flex items-start space-x-4 py-3 border-b border-gray-100 last:border-b-0">
        <div className="w-1/3 pt-2">
          <Label className="text-sm font-medium text-gray-700">{formatFieldName(key)}</Label>
          <p className="text-xs text-gray-500 mt-1">{key}</p>
        </div>

        <div className="flex-1">
          {isEditing ? (
            <div className="space-y-2">
              {value.length > 50 ? (
                <Textarea
                  defaultValue={value}
                  className="w-full"
                  rows={3}
                  onBlur={(e) => {
                    updateValue(key, e.target.value)
                    setEditingField(null)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      updateValue(key, e.currentTarget.value)
                      setEditingField(null)
                    }
                    if (e.key === "Escape") {
                      setEditingField(null)
                    }
                  }}
                  autoFocus
                />
              ) : (
                <Input
                  defaultValue={value}
                  className="w-full"
                  onBlur={(e) => {
                    updateValue(key, e.target.value)
                    setEditingField(null)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      updateValue(key, e.currentTarget.value)
                      setEditingField(null)
                    }
                    if (e.key === "Escape") {
                      setEditingField(null)
                    }
                  }}
                  autoFocus
                />
              )}
              <div className="flex space-x-2">
                <Button
                  size="sm"
                  onClick={() => {
                    const input = document.querySelector(
                      `input[value="${value}"], textarea[value="${value}"]`,
                    ) as HTMLInputElement
                    if (input) {
                      updateValue(key, input.value)
                    }
                    setEditingField(null)
                  }}
                >
                  Save
                </Button>
                <Button size="sm" variant="outline" onClick={() => setEditingField(null)}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between group">
              <div className="flex-1 min-w-0 pr-4">
                <p className="text-sm text-gray-900 break-words">{value}</p>
              </div>
              <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button size="sm" variant="ghost" onClick={() => setEditingField(key)} className="h-8 w-8 p-0">
                  <Edit3 className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => deleteField(key)}
                  className="h-8 w-8 p-0 text-red-500 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Context Data</CardTitle>
            <p className="text-sm text-gray-500 mt-1">{Object.keys(data).length} fields • Click any value to edit</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setIsAddingField(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Field
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search fields..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
      </CardHeader>

      <CardContent className="space-y-1 max-h-96 overflow-y-auto">
        {/* Add new field form */}
        {isAddingField && (
          <div className="mb-4 p-4 bg-blue-50 rounded-lg border-2 border-dashed border-blue-300">
            <div className="space-y-3">
              <div>
                <Label htmlFor="new-field-key" className="text-sm font-medium">
                  Field Key
                </Label>
                <Input
                  id="new-field-key"
                  value={newFieldKey}
                  onChange={(e) => setNewFieldKey(e.target.value)}
                  placeholder="e.g., middle_name"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="new-field-value" className="text-sm font-medium">
                  Field Value
                </Label>
                <Input
                  id="new-field-value"
                  value={newFieldValue}
                  onChange={(e) => setNewFieldValue(e.target.value)}
                  placeholder="Enter value"
                  className="mt-1"
                />
              </div>
              <div className="flex space-x-2">
                <Button size="sm" onClick={addField} disabled={!newFieldKey.trim() || !newFieldValue.trim()}>
                  Add Field
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setIsAddingField(false)
                    setNewFieldKey("")
                    setNewFieldValue("")
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Fields list */}
        {filteredData.length > 0 ? (
          <div className="space-y-1">{filteredData.map(([key, value]) => renderField(key, value))}</div>
        ) : searchTerm ? (
          <div className="text-center py-8 text-gray-500">
            <Search className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No fields found matching &quot;{searchTerm}&quot;</p>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Edit3 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p className="text-lg font-medium">No context data available</p>
            <p className="text-sm">Upload context files to see extracted data here</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
