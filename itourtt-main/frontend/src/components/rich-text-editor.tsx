"use client";

import { useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import TextAlign from "@tiptap/extension-text-align";
import Underline from "@tiptap/extension-underline";
import Image from "@tiptap/extension-image";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  AlignLeft,
  AlignCenter,
  AlignRight,
  ImageIcon,
  TableIcon,
  Plus,
  Minus,
  Trash2,
  Braces,
  Code2,
} from "lucide-react";

interface RichTextEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
  logoUrl?: string | null;
}

function ToolbarButton({
  active,
  onClick,
  children,
  title,
  disabled,
}: {
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
  title?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      disabled={disabled}
      className={`rounded p-1.5 transition-colors ${
        disabled
          ? "text-muted-foreground/30 cursor-not-allowed"
          : active
            ? "bg-primary/20 text-primary"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
      }`}
    >
      {children}
    </button>
  );
}

export function RichTextEditor({
  content,
  onChange,
  placeholder,
  logoUrl,
}: RichTextEditorProps) {
  const [logoSize, setLogoSize] = useState(50);
  // "HTML source" mode — WordPress-style Text tab. When on, the user edits raw
  // HTML in a textarea that is stored verbatim (tiptap's schema can't strip it).
  const [htmlMode, setHtmlMode] = useState(false);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Underline,
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      Image.configure({ inline: false }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class:
          "min-h-[120px] p-3 text-sm text-foreground focus:outline-none prose prose-sm prose-invert max-w-none [&_h1]:text-xl [&_h1]:font-bold [&_h2]:text-lg [&_h2]:font-semibold [&_h3]:text-base [&_h3]:font-medium [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_img]:h-auto [&_img]:my-2 [&_table]:border-collapse [&_table]:w-full [&_table]:my-2 [&_td]:border [&_td]:border-border [&_td]:p-2 [&_td]:text-sm [&_th]:border [&_th]:border-border [&_th]:p-2 [&_th]:text-sm [&_th]:font-semibold [&_th]:bg-muted/50",
      },
    },
  });

  if (!editor) return null;

  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
  const inTable = editor.isActive("table");

  // Switch between visual (tiptap) and raw-HTML source editing.
  const toggleHtmlMode = () => {
    if (htmlMode) {
      // Leaving source mode: load the edited HTML back into the visual editor.
      editor.commands.setContent(content || "", { emitUpdate: false });
    }
    setHtmlMode((v) => !v);
  };

  const getLogoFullUrl = () => {
    if (!logoUrl) return "";
    return logoUrl.startsWith("http") ? logoUrl : `${API_BASE}${logoUrl}`;
  };

  const insertLogo = () => {
    if (!logoUrl) return;
    const fullUrl = getLogoFullUrl();
    editor.chain().focus().setImage({ src: fullUrl }).run();
    updateLogoSize(logoSize);
  };

  const updateLogoSize = (size: number) => {
    const editorEl = document.querySelector(".ProseMirror");
    if (!editorEl) return;
    const imgs = editorEl.querySelectorAll("img");
    imgs.forEach((img) => {
      img.style.width = `${size}%`;
      img.style.maxWidth = `${size}%`;
    });
    setTimeout(() => {
      if (editor) onChange(editor.getHTML());
    }, 50);
  };

  const handleSizeChange = (newSize: number) => {
    setLogoSize(newSize);
    updateLogoSize(newSize);
  };

  return (
    <div className="overflow-hidden rounded-md border border-border bg-muted/50">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-0.5 border-b border-border bg-muted/80 px-2 py-1.5">
        {!htmlMode && (
        <>
        <ToolbarButton
          active={editor.isActive("bold")}
          onClick={() => editor.chain().focus().toggleBold().run()}
          title="Bold"
        >
          <Bold className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive("italic")}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          title="Italic"
        >
          <Italic className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive("underline")}
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          title="Underline"
        >
          <UnderlineIcon className="h-4 w-4" />
        </ToolbarButton>

        <div className="mx-1 h-5 w-px bg-border" />

        <ToolbarButton
          active={editor.isActive("heading", { level: 1 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          title="Heading 1"
        >
          <Heading1 className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive("heading", { level: 2 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          title="Heading 2"
        >
          <Heading2 className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive("heading", { level: 3 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          title="Heading 3"
        >
          <Heading3 className="h-4 w-4" />
        </ToolbarButton>

        <div className="mx-1 h-5 w-px bg-border" />

        <ToolbarButton
          active={editor.isActive("bulletList")}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          title="Bullet list"
        >
          <List className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive("orderedList")}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          title="Ordered list"
        >
          <ListOrdered className="h-4 w-4" />
        </ToolbarButton>

        <div className="mx-1 h-5 w-px bg-border" />

        <ToolbarButton
          active={editor.isActive({ textAlign: "left" })}
          onClick={() => editor.chain().focus().setTextAlign("left").run()}
          title="Align left"
        >
          <AlignLeft className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive({ textAlign: "center" })}
          onClick={() => editor.chain().focus().setTextAlign("center").run()}
          title="Align center"
        >
          <AlignCenter className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive({ textAlign: "right" })}
          onClick={() => editor.chain().focus().setTextAlign("right").run()}
          title="Align right"
        >
          <AlignRight className="h-4 w-4" />
        </ToolbarButton>

        <div className="mx-1 h-5 w-px bg-border" />

        {/* Table controls */}
        <ToolbarButton
          onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}
          title="Insert table"
        >
          <TableIcon className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().addColumnAfter().run()}
          title="Add column"
          disabled={!inTable}
        >
          <span className="flex items-center gap-px"><Plus className="h-3 w-3" /><span className="text-[9px] font-bold">Col</span></span>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().addRowAfter().run()}
          title="Add row"
          disabled={!inTable}
        >
          <span className="flex items-center gap-px"><Plus className="h-3 w-3" /><span className="text-[9px] font-bold">Row</span></span>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().deleteColumn().run()}
          title="Delete column"
          disabled={!inTable}
        >
          <span className="flex items-center gap-px"><Minus className="h-3 w-3" /><span className="text-[9px] font-bold">Col</span></span>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().deleteRow().run()}
          title="Delete row"
          disabled={!inTable}
        >
          <span className="flex items-center gap-px"><Minus className="h-3 w-3" /><span className="text-[9px] font-bold">Row</span></span>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().deleteTable().run()}
          title="Delete table"
          disabled={!inTable}
        >
          <Trash2 className="h-4 w-4" />
        </ToolbarButton>

        {/* Shortcodes */}
        <div className="mx-1 h-5 w-px bg-border" />
        <div className="flex items-center gap-0.5">
          <Braces className="h-3.5 w-3.5 text-muted-foreground/60 mr-0.5" />
          <button
            type="button"
            onClick={() => editor.chain().focus().insertContent("{{reportName}}").run()}
            title="Insert report name shortcode"
            className="rounded px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            Report
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().insertContent("{{dateTime}}").run()}
            title="Insert date/time shortcode"
            className="rounded px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            Date/Time
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().insertContent("{{user}}").run()}
            title="Insert user name shortcode"
            className="rounded px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            User
          </button>
        </div>

        {logoUrl && (
          <>
            <div className="mx-1 h-5 w-px bg-border" />
            <ToolbarButton
              onClick={insertLogo}
              title="Insert company logo"
            >
              <ImageIcon className="h-4 w-4" />
            </ToolbarButton>
            <div className="flex items-center gap-1.5 ml-1">
              <input
                type="range"
                min={10}
                max={100}
                step={5}
                value={logoSize}
                onChange={(e) => handleSizeChange(Number(e.target.value))}
                className="h-1 w-20 cursor-pointer accent-primary"
                title={`Logo size: ${logoSize}%`}
              />
              <span className="text-[10px] text-muted-foreground w-7">{logoSize}%</span>
            </div>
          </>
        )}
        </>
        )}

        {/* HTML source toggle (WordPress-style "Text" tab) */}
        <div className="ml-auto flex items-center gap-1">
          <ToolbarButton
            active={htmlMode}
            onClick={toggleHtmlMode}
            title={htmlMode ? "Back to visual editor" : "Edit HTML source"}
          >
            <Code2 className="h-4 w-4" />
          </ToolbarButton>
        </div>
      </div>

      {/* Editor body — visual or raw-HTML source */}
      {htmlMode ? (
        <textarea
          value={content}
          onChange={(e) => onChange(e.target.value)}
          spellCheck={false}
          placeholder={placeholder ?? "<p>Type or paste HTML…</p>"}
          className="min-h-[200px] w-full resize-y bg-background p-3 font-mono text-xs leading-relaxed text-foreground focus:outline-none"
        />
      ) : (
        <EditorContent editor={editor} />
      )}
    </div>
  );
}
