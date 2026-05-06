import React, { useState, useEffect } from 'react';
import { X, AlertTriangle, Info, CheckCircle, Loader2 } from 'lucide-react';

interface FieldMetadata {
  field_name: string;
  field_type: string;
  description: string;
  default_value: any;
  required: boolean;
  constraints?: {
    min?: number;
    max?: number;
    enum?: string[];
    vendor_restricted?: boolean;
    vendor_restriction_reason?: string;
  };
}

interface PolicyDraft {
  policy_type: string;
  action_type: string;
  default_config: Record<string, any>;
  editable_fields: FieldMetadata[];
  manual_analysis_required: boolean;
  warnings: string[];
}

interface PolicyReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (overrideConfig: Record<string, any>, manualAnalysis: ManualAnalysis) => Promise<void>;
  policyDraft: PolicyDraft | null;
  title: string;
  entityName: string;
  isLoading?: boolean;
}

interface ManualAnalysis {
  reason?: string;
  risk_acknowledgement?: string;
  reviewed_by?: string;
}

export const PolicyReviewModal: React.FC<PolicyReviewModalProps> = ({
  isOpen,
  onClose,
  onApply,
  policyDraft,
  title,
  entityName,
  isLoading = false,
}) => {
  const [overrideConfig, setOverrideConfig] = useState<Record<string, any>>({});
  const [manualAnalysis, setManualAnalysis] = useState<ManualAnalysis>({});
  const [applying, setApplying] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (policyDraft) {
      // Initialize override config with default values
      const initialConfig: Record<string, any> = {};
      policyDraft.editable_fields.forEach(field => {
        initialConfig[field.field_name] = field.default_value;
      });
      setOverrideConfig(initialConfig);
    }
  }, [policyDraft]);

  if (!isOpen || !policyDraft) return null;

  const handleFieldChange = (fieldName: string, value: any) => {
    setOverrideConfig(prev => ({
      ...prev,
      [fieldName]: value,
    }));
  };

  const handleApply = async () => {
    setApplying(true);
    try {
      // Only send fields that differ from defaults
      const changedFields: Record<string, any> = {};
      Object.keys(overrideConfig).forEach(key => {
        const field = policyDraft.editable_fields.find(f => f.field_name === key);
        if (field && overrideConfig[key] !== field.default_value) {
          changedFields[key] = overrideConfig[key];
        }
      });

      await onApply(changedFields, manualAnalysis);
      onClose();
    } catch (error) {
      console.error('Failed to apply policy:', error);
    } finally {
      setApplying(false);
    }
  };

  const renderFieldInput = (field: FieldMetadata) => {
    const value = overrideConfig[field.field_name];
    const isChanged = value !== field.default_value;
    const isVendorRestricted = field.constraints?.vendor_restricted === true;
    const vendorRestrictionReason = field.constraints?.vendor_restriction_reason as string | undefined;

    switch (field.field_type) {
      case 'boolean':
        return (
          <div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={value || false}
                onChange={(e) => handleFieldChange(field.field_name, e.target.checked)}
                disabled={isVendorRestricted}
                className={`rounded border-gray-300 text-blue-600 focus:ring-blue-500 ${
                  isVendorRestricted ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              />
              <span className="text-sm text-gray-700">
                {field.description}
                {isVendorRestricted && (
                  <span
                    className="ml-2 px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded border border-yellow-300"
                    title={vendorRestrictionReason}
                  >
                    Vendor Limited
                  </span>
                )}
              </span>
            </label>
          </div>
        );

      case 'integer':
        return (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {field.field_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              {field.required && <span className="text-red-500 ml-1">*</span>}
              {isVendorRestricted && (
                <span
                  className="ml-2 px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded border border-yellow-300"
                  title={vendorRestrictionReason}
                >
                  Vendor Limited
                </span>
              )}
            </label>
            <input
              type="number"
              value={value || ''}
              onChange={(e) => handleFieldChange(field.field_name, parseInt(e.target.value) || null)}
              min={field.constraints?.min}
              max={field.constraints?.max}
              disabled={isVendorRestricted}
              className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 ${
                isChanged ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
              } ${isVendorRestricted ? 'opacity-50 cursor-not-allowed bg-gray-100' : ''}`}
            />
            <p className="text-xs text-gray-500 mt-1">{field.description}</p>
            {field.constraints && (
              <p className="text-xs text-gray-400 mt-1">
                {field.constraints.min !== undefined && `Min: ${field.constraints.min}`}
                {field.constraints.max !== undefined && ` Max: ${field.constraints.max}`}
              </p>
            )}
          </div>
        );

      case 'string':
        if (field.constraints?.enum) {
          return (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.field_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                {field.required && <span className="text-red-500 ml-1">*</span>}
                {isVendorRestricted && (
                  <span
                    className="ml-2 px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded border border-yellow-300"
                    title={vendorRestrictionReason}
                  >
                    Vendor Limited
                  </span>
                )}
              </label>
              <select
                value={value || ''}
                onChange={(e) => handleFieldChange(field.field_name, e.target.value)}
                disabled={isVendorRestricted}
                className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 ${
                  isChanged ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                } ${isVendorRestricted ? 'opacity-50 cursor-not-allowed bg-gray-100' : ''}`}
              >
                {field.constraints.enum.map(option => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">{field.description}</p>
            </div>
          );
        }
        return (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {field.field_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              {field.required && <span className="text-red-500 ml-1">*</span>}
              {isVendorRestricted && (
                <span
                  className="ml-2 px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded border border-yellow-300"
                  title={vendorRestrictionReason}
                >
                  Vendor Limited
                </span>
              )}
            </label>
            <input
              type="text"
              value={value || ''}
              onChange={(e) => handleFieldChange(field.field_name, e.target.value)}
              disabled={isVendorRestricted}
              className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 ${
                isChanged ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
              } ${isVendorRestricted ? 'opacity-50 cursor-not-allowed bg-gray-100' : ''}`}
            />
            <p className="text-xs text-gray-500 mt-1">{field.description}</p>
          </div>
        );

      case 'array':
        return (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {field.field_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              {isVendorRestricted && (
                <span
                  className="ml-2 px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs rounded border border-yellow-300"
                  title={vendorRestrictionReason}
                >
                  Vendor Limited
                </span>
              )}
            </label>
            <input
              type="text"
              value={Array.isArray(value) ? value.join(', ') : ''}
              onChange={(e) => {
                const arrayValue = e.target.value.split(',').map(v => v.trim()).filter(v => v);
                handleFieldChange(field.field_name, arrayValue);
              }}
              placeholder="Comma-separated values"
              disabled={isVendorRestricted}
              className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 ${
                isChanged ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
              } ${isVendorRestricted ? 'opacity-50 cursor-not-allowed bg-gray-100' : ''}`}
            />
            <p className="text-xs text-gray-500 mt-1">{field.description}</p>
          </div>
        );

      default:
        return null;
    }
  };

  const hasChanges = Object.keys(overrideConfig).some(key => {
    const field = policyDraft.editable_fields.find(f => f.field_name === key);
    return field && overrideConfig[key] !== field.default_value;
  });

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />

        {/* Modal panel */}
        <div className="inline-block w-full max-w-4xl my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-lg">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
              <p className="text-sm text-gray-500 mt-1">{entityName}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 focus:outline-none"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 max-h-[70vh] overflow-y-auto">
            {/* Warnings */}
            {policyDraft.warnings.length > 0 && (
              <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                <div className="flex items-start">
                  <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 mr-3 flex-shrink-0" />
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-yellow-800 mb-2">Warnings</h4>
                    <ul className="text-sm text-yellow-700 space-y-1">
                      {policyDraft.warnings.map((warning, idx) => (
                        <li key={idx}>• {warning}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Policy Type Info */}
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
              <div className="flex items-start">
                <Info className="w-5 h-5 text-blue-600 mt-0.5 mr-3 flex-shrink-0" />
                <div className="flex-1">
                  <h4 className="text-sm font-medium text-blue-800 mb-1">Policy Type</h4>
                  <p className="text-sm text-blue-700">
                    {policyDraft.policy_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </p>
                </div>
              </div>
            </div>

            {/* Editable Fields */}
            <div className="space-y-4 mb-6">
              <h4 className="text-sm font-semibold text-gray-900 mb-3">
                Policy Configuration
                {hasChanges && (
                  <span className="ml-2 text-xs font-normal text-blue-600">
                    (Modified fields highlighted)
                  </span>
                )}
              </h4>
              {policyDraft.editable_fields.map(field => (
                <div key={field.field_name} className="border-b border-gray-100 pb-4 last:border-0">
                  {renderFieldInput(field)}
                </div>
              ))}
            </div>

            {/* Manual Analysis Section */}
            <div className="border-t border-gray-200 pt-6">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center text-sm font-medium text-gray-700 hover:text-gray-900 mb-3"
              >
                <span>{showAdvanced ? '▼' : '▶'}</span>
                <span className="ml-2">Manual Analysis (Optional)</span>
              </button>

              {showAdvanced && (
                <div className="space-y-4 pl-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Reason for Changes
                    </label>
                    <textarea
                      value={manualAnalysis.reason || ''}
                      onChange={(e) => setManualAnalysis(prev => ({ ...prev, reason: e.target.value }))}
                      rows={3}
                      placeholder="Explain why you're modifying the default configuration..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Risk Acknowledgement
                    </label>
                    <textarea
                      value={manualAnalysis.risk_acknowledgement || ''}
                      onChange={(e) => setManualAnalysis(prev => ({ ...prev, risk_acknowledgement: e.target.value }))}
                      rows={2}
                      placeholder="Acknowledge any risks associated with these changes..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Reviewed By
                    </label>
                    <input
                      type="text"
                      value={manualAnalysis.reviewed_by || ''}
                      onChange={(e) => setManualAnalysis(prev => ({ ...prev, reviewed_by: e.target.value }))}
                      placeholder="Your name or email"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center text-sm text-gray-600">
              {hasChanges && (
                <div className="flex items-center">
                  <CheckCircle className="w-4 h-4 text-blue-600 mr-2" />
                  <span>Configuration modified</span>
                </div>
              )}
            </div>
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                disabled={applying}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleApply}
                disabled={applying || isLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {applying && <Loader2 className="w-4 h-4 animate-spin" />}
                {applying ? 'Applying...' : hasChanges ? 'Apply with Changes' : 'Apply Defaults'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Made with Bob
