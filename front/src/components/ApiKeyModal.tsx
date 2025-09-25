"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Key, Plus, Trash2, Eye, EyeOff, AlertCircle, Loader2 } from "lucide-react"
import React from "react"
import { READ_API_KEYS_CHANNEL } from "@/helpers/ipc/file/file-channels"

interface ApiKey {
  provider: string;
  key: string;
}

interface ApiKeyModalProps {
  isOpen: boolean
  onClose: () => void
  selectedProvider: string
  onProviderChange: (provider: string) => void
}

const PROVIDERS = ["local", "anythingllm", "openai", "groq"];

const apiKeyService = {
  async getApiKeys(): Promise<ApiKey[]> {
    try {
      const fileData = await window.fileContext.readApiKeys();
      if (fileData) {
        return fileData;
      }
      return [];
    } catch (e) {
      console.error("Failed to fetch API keys:", e);
      return [];
    }
  },
  async saveApiKeys(keys: ApiKey[]): Promise<void> {
    try {
      await window.fileContext.writeApiKeys(keys);
    } catch (e) {
      console.error("Failed to save API keys:", e);
    }
  },
  async saveApiKey(newApiKey: ApiKey): Promise<void> {
    const keys = await this.getApiKeys();
    const updatedKeys = keys.filter((key) => key.provider !== newApiKey.provider);
    updatedKeys.push(newApiKey);
    await this.saveApiKeys(updatedKeys);
  },
  async deleteApiKey(provider: string): Promise<void> {
    const keys = await this.getApiKeys();
    const updatedKeys = keys.filter((key) => key.provider !== provider);
    await this.saveApiKeys(updatedKeys);
  },
}

export default function ApiKeyModal({ isOpen, onClose, selectedProvider, onProviderChange }: ApiKeyModalProps) {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [newKeyProvider, setNewKeyProvider] = useState(selectedProvider)
  const [newKeyValue, setNewKeyValue] = useState("")

  useEffect(() => {
    if (isOpen) {
      loadApiKeys();
    }
  }, [isOpen]);

  const loadApiKeys = async () => {
    setLoading(true);
    try {
      const keys = await apiKeyService.getApiKeys();
      setApiKeys(keys);
    } catch (error) {
      console.error("Failed to load API keys:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddApiKey = async () => {
    if (!newKeyProvider || !newKeyValue.trim()) return;

    setSaving(true);
    try {
      const newApiKey: ApiKey = {
        provider: newKeyProvider,
        key: newKeyValue.trim(),
      };
      await apiKeyService.saveApiKey(newApiKey);
      setApiKeys((prev) => {
        const updated = prev.filter((key) => key.provider !== newApiKey.provider);
        updated.push(newApiKey);
        return updated;
      });
      setNewKeyValue("");
    } catch (error) {
      console.error("Failed to save API key:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteApiKey = async (provider: string) => {
    try {
      await apiKeyService.deleteApiKey(provider);
      setApiKeys((prev) => prev.filter((key) => key.provider !== provider));
    } catch (error) {
      console.error("Failed to delete API key:", error);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[75vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Key className="h-5 w-5" />
            <span>API Key Management</span>
          </DialogTitle>
          <DialogDescription>
            Manage your AI provider API keys. Only one key per provider is allowed.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="manage" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="manage">Manage Keys</TabsTrigger>
            <TabsTrigger value="add">Add New Key</TabsTrigger>
          </TabsList>

          <TabsContent value="manage" className="space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                <span className="ml-2 text-gray-600">Loading API keys...</span>
              </div>
            ) : apiKeys.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-8">
                  <Key className="h-12 w-12 text-gray-300 mb-4" />
                  <p className="text-gray-500 text-center">No API keys found</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-2">
                {apiKeys.map((apiKey) => (
                  <Card key={apiKey.provider}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{apiKey.provider}</p>
                          <p className="text-sm text-gray-600 mt-1">{apiKey.key}</p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteApiKey(apiKey.provider)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="add" className="space-y-4">
            <Card>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="key-provider">Provider</Label>
                  <select
                    id="key-provider"
                    value={newKeyProvider}
                    onChange={(e) => setNewKeyProvider(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {PROVIDERS.map((provider) => (
                      <option key={provider} value={provider}>
                        {provider}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="key-value">API Key</Label>
                  <Input
                    id="key-value"
                    type="password"
                    placeholder="Enter your API key"
                    value={newKeyValue}
                    onChange={(e) => setNewKeyValue(e.target.value)}
                  />
                </div>

                <div className="flex justify-end space-x-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setNewKeyProvider(selectedProvider);
                      setNewKeyValue("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleAddApiKey} disabled={!newKeyProvider || !newKeyValue.trim() || saving}>
                    {saving ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        Add API Key
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end pt-4 border-t">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
