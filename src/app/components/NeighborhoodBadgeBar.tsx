'use client';

import React from 'react';
import { NEIGHBORHOODS, getNeighborhoodLabel } from '../data/neighborhoods';

interface NeighborhoodBadgeBarProps {
  /** Set of neighborhood IDs that have at least one restaurant in the current dataset */
  coveredIds: Set<string>;
  /** Currently selected neighborhood filter (undefined = all) */
  selectedId?: string;
  /** Called when a badge is clicked */
  onSelect: (id: string | undefined) => void;
}

export default function NeighborhoodBadgeBar({
  coveredIds,
  selectedId,
  onSelect,
}: NeighborhoodBadgeBarProps) {
  const covered = NEIGHBORHOODS.filter((n) => coveredIds.has(n.id));
  const uncovered = NEIGHBORHOODS.filter((n) => !coveredIds.has(n.id));

  const Badge = ({
    id,
    label,
    active,
    disabled,
  }: {
    id: string;
    label: string;
    active: boolean;
    disabled: boolean;
  }) => (
    <button
      type="button"
      onClick={() => !disabled && onSelect(active ? undefined : id)}
      disabled={disabled}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
        disabled
          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
          : active
            ? 'bg-emerald-600 text-white'
            : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
      }`}
    >
      {!disabled && (
        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
      )}
      {label}
    </button>
  );

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide mr-1">
          Coverage
        </span>
        {covered.map((n) => (
          <Badge
            key={n.id}
            id={n.id}
            label={getNeighborhoodLabel(n.id)}
            active={selectedId === n.id}
            disabled={false}
          />
        ))}
        {uncovered.map((n) => (
          <Badge
            key={n.id}
            id={n.id}
            label={getNeighborhoodLabel(n.id)}
            active={false}
            disabled={true}
          />
        ))}
        <span className="text-xs text-gray-400 ml-1">
          (these are neighborhoods I find myself in —{' '}
          <a
            href="mailto:ruslan+happyhours@rosipov.com"
            className="underline hover:text-gray-600"
          >
            email me
          </a>{' '}
          if you want your neighborhood included)
        </span>
      </div>
      {selectedId && (
        <button
          type="button"
          onClick={() => onSelect(undefined)}
          className="text-xs text-gray-400 hover:text-gray-600 underline self-start"
        >
          Clear neighborhood filter
        </button>
      )}
    </div>
  );
}
