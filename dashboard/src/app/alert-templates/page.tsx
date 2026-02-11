'use client';

import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Mail, Eye, EyeOff, AlertTriangle, RefreshCw } from 'lucide-react';
import { SkeletonCard } from '../../components/Skeleton';
import { RefreshButton } from '../../components/Loading';
import { useToast } from '../../components/ToastProvider';
import { ConfirmationDialog } from '../../components/ConfirmationDialog';

interface AlertTemplate {
  id: number;
  name: string;
  description: string | null;
  subject_template: string;
  html_template: string;
  text_template: string;
  severity_filter: string[] | null;
  category_filter: string[] | null;
  is_default: boolean;
  is_system: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export default function AlertTemplatesPage() {
  const [templates, setTemplates] = useState<AlertTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<AlertTemplate | null>(null);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{ isOpen: boolean; template: AlertTemplate | null }>({
    isOpen: false,
    template: null
  });
  const { error: showError, success } = useToast();

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/alerts/templates/');
      if (response.ok) {
        const data = await response.json();
        setTemplates(data);
      } else {
        const errorMessage = `Failed to fetch templates: ${response.statusText}`;
        setError(errorMessage);
        showError('Fetch Error', errorMessage);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch templates';
      setError(errorMessage);
      showError('Network Error', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (template: AlertTemplate) => {
    setDeleteConfirmation({ isOpen: true, template });
  };

  const confirmDelete = async () => {
    if (!deleteConfirmation.template) return;

    const templateId = deleteConfirmation.template.id;
    setDeleteConfirmation({ isOpen: false, template: null });

    try {
      const response = await fetch(`/api/alerts/templates/${templateId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setTemplates(templates.filter(t => t.id !== templateId));
        success('Template Deleted', 'Alert template has been successfully deleted.');
      } else {
        const errorMessage = `Failed to delete template: ${response.statusText}`;
        showError('Delete Error', errorMessage);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete template';
      showError('Network Error', errorMessage);
    }
  };

  const cancelDelete = () => {
    setDeleteConfirmation({ isOpen: false, template: null });
  };

  const handleToggleEnabled = async (template: AlertTemplate) => {
    try {
      const response = await fetch(`/api/alerts/templates/${template.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          enabled: !template.enabled,
        }),
      });

      if (response.ok) {
        const updatedTemplate = await response.json();
        setTemplates(templates.map(t =>
          t.id === template.id ? updatedTemplate : t
        ));
        success('Template Updated', `Template has been ${updatedTemplate.enabled ? 'enabled' : 'disabled'}.`);
      } else {
        const errorMessage = `Failed to update template: ${response.statusText}`;
        showError('Update Error', errorMessage);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update template';
      showError('Network Error', errorMessage);
    }
  };

  const handleSetDefault = async (template: AlertTemplate) => {
    try {
      const response = await fetch(`/api/alerts/templates/${template.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          is_default: true,
        }),
      });

      if (response.ok) {
        const updatedTemplate = await response.json();
        setTemplates(templates.map(t => ({
          ...t,
          is_default: t.id === template.id ? true : false
        })));
        success('Default Template Set', `${template.name} is now the default template.`);
      } else {
        const errorMessage = `Failed to set default template: ${response.statusText}`;
        showError('Update Error', errorMessage);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to set default template';
      showError('Network Error', errorMessage);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Alert Templates</h1>
            <p className="text-muted-foreground">Customize alert notification messages</p>
          </div>
        </div>
        <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-surface-2 rounded w-1/4"></div>
            <div className="h-4 bg-surface-2 rounded w-1/2"></div>
            <div className="h-4 bg-surface-2 rounded w-3/4"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Alert Templates</h1>
          <p className="text-muted-foreground">Customize alert notification messages and formatting</p>
        </div>
        <div className="flex items-center gap-2">
          <RefreshButton onClick={fetchTemplates} loading={loading} />
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-vanguard-600 hover:bg-vanguard-700 text-white rounded-lg transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Template
          </button>
        </div>
      </div>

      <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6">
        <div className="space-y-4">
          {loading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : error ? (
            <div className="text-center py-8">
              <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">Failed to Load Templates</h3>
              <p className="text-muted-foreground mb-4">{error}</p>
              <button
                onClick={fetchTemplates}
                className="px-4 py-2 bg-vanguard-600 hover:bg-vanguard-700 text-white rounded-lg transition-colors flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-8">
              <Mail className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No Alert Templates</h3>
              <p className="text-muted-foreground mb-4">
                Create your first alert template to customize notification messages.
              </p>
              <button
                onClick={() => setShowCreateForm(true)}
                className="px-4 py-2 bg-vanguard-600 hover:bg-vanguard-700 text-white rounded-lg transition-colors"
              >
                Create Template
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className="border border-white/[0.06] rounded-lg p-4 hover:bg-surface-2/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-medium">{template.name}</h3>
                        {template.is_default && (
                          <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded">
                            Default
                          </span>
                        )}
                        {template.is_system && (
                          <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">
                            System
                          </span>
                        )}
                        {!template.enabled && (
                          <span className="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded">
                            Disabled
                          </span>
                        )}
                      </div>

                      {template.description && (
                        <p className="text-sm text-muted-foreground mb-2">
                          {template.description}
                        </p>
                      )}

                      <div className="text-xs text-muted-foreground space-y-1">
                        <div>Subject: <code className="bg-surface-2 px-1 rounded">{template.subject_template}</code></div>
                        {template.severity_filter && template.severity_filter.length > 0 && (
                          <div>Severities: {template.severity_filter.join(', ')}</div>
                        )}
                        {template.category_filter && template.category_filter.length > 0 && (
                          <div>Categories: {template.category_filter.join(', ')}</div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 ml-4">
                      {!template.is_system && (
                        <>
                          <button
                            onClick={() => handleSetDefault(template)}
                            disabled={template.is_default}
                            className="p-1 text-muted-foreground hover:text-green-400 disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Set as default"
                          >
                            ★
                          </button>

                          <button
                            onClick={() => handleToggleEnabled(template)}
                            className={`p-1 ${template.enabled ? 'text-green-400 hover:text-gray-400' : 'text-gray-400 hover:text-green-400'}`}
                            title={template.enabled ? 'Disable template' : 'Enable template'}
                          >
                            {template.enabled ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                          </button>

                          <button
                            onClick={() => setEditingTemplate(template)}
                            className="p-1 text-muted-foreground hover:text-blue-400"
                            title="Edit template"
                          >
                            <Edit className="w-4 h-4" />
                          </button>

                          <button
                            onClick={() => handleDelete(template)}
                            className="p-1 text-muted-foreground hover:text-red-400"
                            title="Delete template"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create/Edit Form Modal would go here */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6 w-full max-w-2xl mx-4">
            <h2 className="text-xl font-bold mb-4">Create Alert Template</h2>
            <p className="text-muted-foreground mb-4">
              This feature is coming soon. For now, templates can be managed via the API.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 bg-surface-2 hover:bg-surface-2/80 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {editingTemplate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-1 rounded-xl border border-white/[0.06] p-6 w-full max-w-2xl mx-4">
            <h2 className="text-xl font-bold mb-4">Edit Alert Template</h2>
            <p className="text-muted-foreground mb-4">
              Template editing is coming soon. For now, templates can be managed via the API.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditingTemplate(null)}
                className="px-4 py-2 bg-surface-2 hover:bg-surface-2/80 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmationDialog
        isOpen={deleteConfirmation.isOpen}
        title="Delete Alert Template"
        message={`Are you sure you want to delete "${deleteConfirmation.template?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
        type="danger"
      />
    </div>
  );
}