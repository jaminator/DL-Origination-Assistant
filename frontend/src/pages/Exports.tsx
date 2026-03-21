import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageSpinner } from '@/components/ui/Spinner';
import { useStore } from '@/hooks/useStore';
import { formatDate } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { Download, FileSpreadsheet, FileText, FileJson } from 'lucide-react';

const FORMATS = [
  {
    id: 'excel',
    label: 'Excel',
    icon: <FileSpreadsheet className="h-8 w-8 text-green-600" />,
    description: '4-sheet workbook: Priority Outreach, Capital Structure, Enrichment Sources, Master Universe',
    recommended: true,
  },
  {
    id: 'csv',
    label: 'CSV',
    icon: <FileText className="h-8 w-8 text-blue-600" />,
    description: 'Flat file with all companies and key fields',
  },
  {
    id: 'json',
    label: 'JSONL',
    icon: <FileJson className="h-8 w-8 text-purple-600" />,
    description: 'Full company records, one per line, for programmatic use',
  },
];

export function Exports() {
  const { runId } = useParams();
  const queryClient = useQueryClient();
  const addToast = useStore((s) => s.addToast);
  const [selectedFormat, setSelectedFormat] = useState('excel');

  const { data: exports, isLoading } = useQuery({
    queryKey: ['exports', runId],
    queryFn: () => api.listExports(runId!),
    enabled: !!runId,
  });

  const exportMutation = useMutation({
    mutationFn: () => api.triggerExport(runId!, selectedFormat),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exports', runId] });
      addToast({ type: 'success', message: 'Export generated successfully' });
    },
    onError: (err) => addToast({ type: 'error', message: err.message }),
  });

  if (isLoading) return <PageSpinner />;

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-slate-900">Export Results</h1>
        <p className="text-sm text-slate-500 mt-1">Generate and download outreach-ready files</p>
      </div>

      {/* Format selection cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {FORMATS.map((fmt) => (
          <button
            key={fmt.id}
            onClick={() => setSelectedFormat(fmt.id)}
            className={cn(
              'rounded-lg border-2 p-4 text-left transition-colors',
              selectedFormat === fmt.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-slate-200 bg-white hover:border-slate-300',
            )}
          >
            <div className="flex items-center gap-2 mb-2">
              {fmt.icon}
              <span className="font-medium text-slate-900">{fmt.label}</span>
              {fmt.recommended && <Badge variant="primary">Recommended</Badge>}
            </div>
            <p className="text-xs text-slate-500">{fmt.description}</p>
          </button>
        ))}
      </div>

      <Button onClick={() => exportMutation.mutate()} loading={exportMutation.isPending} className="mb-8">
        <Download className="h-4 w-4" />
        Generate {FORMATS.find((f) => f.id === selectedFormat)?.label} Export
      </Button>

      {/* Previous exports */}
      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">Previous Exports</h2>
        {!exports?.length ? (
          <EmptyState
            icon={<Download className="h-10 w-10" />}
            title="No exports yet"
            description="Generate an export to create downloadable files."
          />
        ) : (
          <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="text-left px-4 py-2 font-medium text-slate-600">Format</th>
                  <th className="text-left px-4 py-2 font-medium text-slate-600">Created</th>
                  <th className="w-28" />
                </tr>
              </thead>
              <tbody>
                {exports.map((exp) => (
                  <tr key={exp.id} className="border-b border-slate-100">
                    <td className="px-4 py-2">
                      <Badge variant="outline">{(exp.data as Record<string, string>)?.format ?? 'unknown'}</Badge>
                    </td>
                    <td className="px-4 py-2 text-xs text-slate-500">{formatDate(exp.created_at)}</td>
                    <td className="px-4 py-2 text-right">
                      <a
                        href={api.getExportDownloadUrl(runId!, exp.id)}
                        className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                      >
                        Download
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
