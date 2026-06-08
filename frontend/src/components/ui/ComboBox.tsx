import { useState, useRef, useEffect } from 'react';

interface ComboBoxOption {
  value: string | number;
  label: string;
}

interface ComboBoxProps {
  value: string | number;
  onChange: (value: string | number) => void;
  options: ComboBoxOption[];
  placeholder?: string;
  emptyMessage?: string;
}

export function ComboBox({
  value,
  onChange,
  options,
  placeholder = '请选择',
  emptyMessage = '无匹配结果',
}: ComboBoxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedOption = options.find((o) => o.value === value);

  const filtered = searchText
    ? options.filter((o) =>
        o.label.toLowerCase().includes(searchText.toLowerCase()),
      )
    : options;

  // 搜索文字变化时重置高亮
  useEffect(() => {
    setHighlightedIndex(0);
  }, [searchText]);

  // 点击外部关闭
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setSearchText('');
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const selectOption = (opt: ComboBoxOption) => {
    onChange(opt.value);
    setSearchText('');
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'Enter' || e.key === 'ArrowDown') {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (filtered.length > 0) {
          setHighlightedIndex((prev) => (prev + 1) % filtered.length);
        }
        break;
      case 'ArrowUp':
        e.preventDefault();
        if (filtered.length > 0) {
          setHighlightedIndex(
            (prev) => (prev - 1 + filtered.length) % filtered.length,
          );
        }
        break;
      case 'Enter':
        e.preventDefault();
        if (filtered[highlightedIndex]) {
          selectOption(filtered[highlightedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        setSearchText('');
        break;
    }
  };

  const handleClear = () => {
    onChange('');
    setSearchText('');
    setIsOpen(true);
    inputRef.current?.focus();
  };

  const hasValue = value !== '' && value !== undefined;

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus-within:ring-2 focus-within:ring-blue-500">
        <input
          ref={inputRef}
          type="text"
          autoComplete="off"
          className="flex-1 outline-none bg-transparent"
          placeholder={selectedOption ? selectedOption.label : placeholder}
          value={searchText}
          onChange={(e) => {
            setSearchText(e.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
        />
        {hasValue && (
          <button
            type="button"
            className="text-gray-400 hover:text-gray-600 ml-1"
            onClick={handleClear}
            tabIndex={-1}
          >
            &times;
          </button>
        )}
        <span className="text-gray-400 ml-1 pointer-events-none text-[10px]">&#9660;</span>
      </div>
      {isOpen && (
        <ul className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded shadow-lg max-h-48 overflow-y-auto">
          {filtered.length === 0 ? (
            <li className="px-2 py-1 text-sm text-gray-400">{emptyMessage}</li>
          ) : (
            filtered.map((opt, idx) => (
              <li
                key={opt.value}
                className={`px-2 py-1 text-sm cursor-pointer hover:bg-blue-50 ${
                  idx === highlightedIndex ? 'bg-blue-100' : ''
                }`}
                onClick={() => selectOption(opt)}
                onMouseEnter={() => setHighlightedIndex(idx)}
              >
                {opt.label}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
