#!/usr/bin/env python3
"""MCP server for Tax PDF extraction - allows agent to extract tax forms directly."""

import json
from pathlib import Path
from typing import Any

import mcp.server.stdio
from mcp.types import Tool, TextContent, ToolResult

from tax_agent.statement_parser import parse_tax_return_summary, get_pdf_extraction_status


server = mcp.server.stdio.StdioServer()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tax extraction tools."""
    return [
        Tool(
            name="extract_tax_file",
            description="Extract tax form data from a single PDF (W2, 1099-NEC, 1099-INT, Form 1040, etc.). Returns form type and extracted fields.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the PDF file to extract (e.g., C:\\Users\\jobarbar\\Documents\\2025_taxes\\form_1040.pdf)"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="extract_tax_folder",
            description="Batch extract tax forms from all PDFs in a folder. Returns summary of all extracted documents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute path to folder containing PDF files (e.g., C:\\Users\\jobarbar\\Documents\\2025_taxes)"
                    }
                },
                "required": ["folder_path"]
            }
        ),
        Tool(
            name="check_extraction_status",
            description="Check if all required PDF extraction dependencies are installed and working.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> ToolResult:
    """Execute tax extraction tools."""
    
    if name == "extract_tax_file":
        return _extract_single_file(arguments.get("file_path"))
    
    elif name == "extract_tax_folder":
        return _extract_folder(arguments.get("folder_path"))
    
    elif name == "check_extraction_status":
        return _check_status()
    
    else:
        return ToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True
        )


def _extract_single_file(file_path: str | None) -> ToolResult:
    """Extract a single tax file."""
    if not file_path:
        return ToolResult(
            content=[TextContent(type="text", text="Error: file_path is required")],
            isError=True
        )
    
    try:
        path = Path(file_path)
        if not path.exists():
            return ToolResult(
                content=[TextContent(type="text", text=f"Error: File not found: {file_path}")],
                isError=True
            )
        
        summary = parse_tax_return_summary(path)
        if not summary:
            return ToolResult(
                content=[TextContent(type="text", text=f"Error: Could not extract data from {file_path}")],
                isError=True
            )
        
        result_dict = {
            "source_file": summary.source_file,
            "form_type": summary.form_type,
            "filing_year": summary.filing_year,
            "extracted_fields": {
                "total_income": summary.total_income,
                "adjusted_gross_income": summary.adjusted_gross_income,
                "deductions": summary.deductions,
                "taxable_income": summary.taxable_income,
                "total_tax": summary.total_tax,
                "total_withholding": summary.total_withholding,
                "refund_or_owed": summary.refund if summary.refund else summary.amount_you_owe,
                "wages": summary.wages,
                "federal_income_tax_withheld": summary.federal_income_tax_withheld,
                "nonemployee_compensation": summary.nonemployee_compensation,
                "interest_income": summary.interest_income,
                "ordinary_dividends": summary.ordinary_dividends,
            }
        }
        
        output = json.dumps(result_dict, indent=2)
        return ToolResult(content=[TextContent(type="text", text=output)])
    
    except Exception as e:
        return ToolResult(
            content=[TextContent(type="text", text=f"Error extracting file: {str(e)}")],
            isError=True
        )


def _extract_folder(folder_path: str | None) -> ToolResult:
    """Extract all tax files from a folder."""
    if not folder_path:
        return ToolResult(
            content=[TextContent(type="text", text="Error: folder_path is required")],
            isError=True
        )
    
    try:
        path = Path(folder_path)
        if not path.is_dir():
            return ToolResult(
                content=[TextContent(type="text", text=f"Error: Not a directory: {folder_path}")],
                isError=True
            )
        
        # Find all PDF files in folder
        pdf_files = list(path.glob("*.pdf")) + list(path.glob("**/*.pdf"))
        if not pdf_files:
            return ToolResult(
                content=[TextContent(type="text", text=f"No PDF files found in {folder_path}")],
                isError=True
            )
        
        results = {
            "folder": folder_path,
            "total_files": len(pdf_files),
            "extracted_documents": []
        }
        
        for pdf_file in sorted(pdf_files):
            try:
                summary = parse_tax_return_summary(pdf_file)
                if summary:
                    doc_dict = {
                        "file": pdf_file.name,
                        "form_type": summary.form_type,
                        "filing_year": summary.filing_year,
                        "agi": summary.adjusted_gross_income,
                        "total_income": summary.total_income,
                        "withholding": summary.total_withholding,
                        "refund_owed": summary.refund if summary.refund else summary.amount_you_owe,
                    }
                    results["extracted_documents"].append(doc_dict)
            except Exception as e:
                results["extracted_documents"].append({
                    "file": pdf_file.name,
                    "error": str(e)
                })
        
        output = json.dumps(results, indent=2)
        return ToolResult(content=[TextContent(type="text", text=output)])
    
    except Exception as e:
        return ToolResult(
            content=[TextContent(type="text", text=f"Error extracting folder: {str(e)}")],
            isError=True
        )


def _check_status() -> ToolResult:
    """Check extraction status."""
    status = get_pdf_extraction_status()
    output = json.dumps(status, indent=2)
    return ToolResult(content=[TextContent(type="text", text=output)])


async def main():
    """Run MCP server."""
    async with server:
        pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
