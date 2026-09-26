import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export function Pagination({
  currentPage = 1,
  totalPages = 1,
  totalItems = 0,
  pageSize = 20,
  onPageChange,
  className = '',
}) {
  if (totalPages <= 1 && totalItems <= pageSize) return null;

  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  return (
    <div className={`flex items-center justify-between px-4 py-3 border-t border-[#E2E8F0] bg-[#F8FAFC] text-xs text-[#64748B] ${className}`}>
      <div>
        Showing <span className="font-semibold text-[#0F172A]">{startItem}</span> to{' '}
        <span className="font-semibold text-[#0F172A]">{endItem}</span> of{' '}
        <span className="font-semibold text-[#0F172A]">{totalItems}</span> records
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(Math.max(1, currentPage - 1))}
          disabled={currentPage <= 1}
          className="p-1.5 rounded-lg border border-[#CBD5E1] bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-[#0F172A] shadow-2xs transition"
          aria-label="Previous page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <span className="px-2 font-mono text-[#0F172A] font-medium">
          Page {currentPage} of {Math.max(1, totalPages)}
        </span>

        <button
          onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage >= totalPages}
          className="p-1.5 rounded-lg border border-[#CBD5E1] bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed text-[#0F172A] shadow-2xs transition"
          aria-label="Next page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default Pagination;
