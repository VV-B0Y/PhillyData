#!/usr/bin/env python3
"""Python recreation of the PhillyData app."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.parse import quote
from urllib.request import urlopen

BASE_URL = "https://phl.carto.com/api/v2/sql?q="


@dataclass(frozen=True)
class Dataset:
    name: str
    title: str
    query: str
    columns: list[str]
    filter_column: str
    include_map_link: bool = False


DATASETS: dict[str, Dataset] = {
    "ppd": Dataset(
        name="ppd",
        title="Philadelphia Police Dept. Salary Info",
        query="SELECT * FROM employee_earnings WHERE department_name = 'PPD Police' AND calendar_year = '2024'",
        columns=[
            "last_name",
            "first_name",
            "title",
            "base_salary",
            "overtime_gross_pay_qtd",
            "base_gross_pay_qtd",
            "longevity_gross_pay_qtd",
            "miscellaneous_gross_pay_qtd",
            "department_name",
            "calendar_year",
        ],
        filter_column="last_name",
    ),
    "violations": Dataset(
        name="violations",
        title="License and Inspections Violations",
        query="SELECT * FROM violations WHERE casecreateddate >= current_date - 20 AND violationstatus = 'OPEN'",
        columns=[
            "opa_owner",
            "violationcodetitle",
            "address",
            "zip",
            "casetype",
            "casestatus",
            "caseprioritydesc",
            "violationdate",
            "violationstatus",
            "caseresponsibility",
        ],
        filter_column="opa_owner",
    ),
    "complaints": Dataset(
        name="complaints",
        title="311 Complaints",
        query="SELECT * FROM complaints WHERE complaintdate >= current_date - 20",
        columns=[
            "opa_owner",
            "address",
            "zip",
            "complaintcodename",
            "complaintdate",
            "complaintstatus",
            "complaintnumber",
            "complaintcode",
            "ticket_num_311",
        ],
        filter_column="opa_owner",
    ),
    "public_cases": Dataset(
        name="public_cases",
        title="311 Public Cases",
        query="SELECT * FROM public_cases_fc WHERE requested_datetime >= current_date - 20",
        columns=[
            "address",
            "requested_datetime",
            "status",
            "zipcode",
            "service_name",
            "agency_responsible",
            "service_notice",
            "status_notes",
            "media_url",
            "lat",
            "lon",
        ],
        filter_column="address",
    ),
    "crime": Dataset(
        name="crime",
        title="Crime Data",
        query="SELECT * FROM incidents_part1_part2 WHERE dispatch_date_time >= current_date - 150",
        columns=[
            "dispatch_date",
            "dispatch_time",
            "location_block",
            "text_general_code",
            "dc_dist",
            "open_map",
        ],
        filter_column="location_block",
        include_map_link=True,
    ),
}


def _fetch_dataset_rows(dataset: Dataset) -> list[dict[str, Any]]:
    url = BASE_URL + quote(dataset.query, safe="")
    with urlopen(url, timeout=30) as response:
        payload = json.load(response)

    rows = payload.get("rows", [])
    normalized: list[dict[str, Any]] = []

    for row in rows:
        item: dict[str, Any] = {column: row.get(column) for column in dataset.columns if column != "open_map"}
        if dataset.include_map_link:
            point_y = row.get("point_y")
            point_x = row.get("point_x")
            item["open_map"] = (
                f"https://www.google.com/maps/@{point_y},{point_x},18z"
                if point_y is not None and point_x is not None
                else ""
            )
        normalized.append(item)

    return normalized


class PhillyDataApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("PhillyData login")
        self.root.geometry("1100x700")

        self.current_dataset: Dataset | None = None
        self.raw_rows: list[dict[str, Any]] = []
        self.filtered_rows: list[dict[str, Any]] = []

        self._build_login_view()

    def _build_login_view(self) -> None:
        self.login_frame = ttk.Frame(self.root, padding=25)
        self.login_frame.pack(fill="both", expand=True)

        ttk.Label(self.login_frame, text="Username").pack(pady=(0, 6))
        self.username_entry = ttk.Entry(self.login_frame, width=28)
        self.username_entry.pack()

        ttk.Label(self.login_frame, text="Password").pack(pady=(16, 6))
        self.password_entry = ttk.Entry(self.login_frame, width=28, show="*")
        self.password_entry.pack()

        self.login_error_var = tk.StringVar(value="")
        ttk.Label(self.login_frame, textvariable=self.login_error_var, foreground="red").pack(pady=(10, 0))

        ttk.Button(self.login_frame, text="Login", command=self._login).pack(pady=(20, 0))
        self.username_entry.focus_set()

    def _build_main_view(self) -> None:
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        sidebar = ttk.Frame(self.main_frame, padding=10)
        sidebar.pack(side="left", fill="y")

        ttk.Button(sidebar, text="Dashboard", command=self._show_dashboard).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="PPD Salary info", command=lambda: self._load_dataset("ppd")).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="LI Violations", command=lambda: self._load_dataset("violations")).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="311 Complaints", command=lambda: self._load_dataset("complaints")).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="Public cases", command=lambda: self._load_dataset("public_cases")).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="Crime Data", command=lambda: self._load_dataset("crime")).pack(fill="x", pady=4)

        content = ttk.Frame(self.main_frame, padding=10)
        content.pack(side="left", fill="both", expand=True)

        search_row = ttk.Frame(content)
        search_row.pack(fill="x", pady=(0, 8))
        ttk.Label(search_row, text="Search").pack(side="left")
        self.search_var = tk.StringVar(value="")
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.status_var = tk.StringVar(value="Load a dataset")
        ttk.Label(content, textvariable=self.status_var).pack(fill="x", pady=(0, 8))

        table_frame = ttk.Frame(content)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        y_scroll.pack(side="right", fill="y")
        x_scroll = ttk.Scrollbar(content, orient="horizontal", command=self.tree.xview)
        x_scroll.pack(fill="x")

        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.bind("<Double-1>", self._open_map_link)

        self._show_dashboard()

    def _login(self) -> None:
        if self.username_entry.get().strip() == "admin":
            self.login_frame.destroy()
            self._build_main_view()
            self.root.title("City of Philadelphia Data")
        else:
            self.login_error_var.set("login failed")

    def _show_dashboard(self) -> None:
        self.current_dataset = None
        self.raw_rows = []
        self.filtered_rows = []
        self.search_var.set("")
        self._set_columns([])
        self.status_var.set("Dashboard")
        self.root.title("City of Philadelphia Data")

    def _load_dataset(self, key: str) -> None:
        dataset = DATASETS[key]
        self.current_dataset = dataset
        self.status_var.set(f"Loading {dataset.title}...")
        self.root.title(f"{dataset.title}: loading")

        def worker() -> None:
            try:
                rows = _fetch_dataset_rows(dataset)
                self.root.after(0, lambda: self._on_rows_loaded(dataset, rows))
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                self.root.after(0, lambda: self._on_load_error(dataset, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_rows_loaded(self, dataset: Dataset, rows: list[dict[str, Any]]) -> None:
        if self.current_dataset != dataset:
            return

        self.raw_rows = rows
        self.search_var.set("")
        self._set_columns(dataset.columns)
        self._render_rows(rows)

        count = len(rows)
        self.status_var.set(f"{dataset.title}: {count} records found")
        self.root.title(f"{dataset.title}: {count} records found")

    def _on_load_error(self, dataset: Dataset, exc: Exception) -> None:
        if self.current_dataset != dataset:
            return

        self.raw_rows = []
        self.filtered_rows = []
        self._set_columns(dataset.columns)
        self._render_rows([])

        self.status_var.set(f"Failed to load {dataset.title}")
        self.root.title(f"{dataset.title}: error")
        messagebox.showerror("Dataset load failed", f"Could not load {dataset.title}.\n\n{exc}")

    def _set_columns(self, columns: list[str]) -> None:
        self.tree["columns"] = columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=160, anchor="w")

    def _render_rows(self, rows: list[dict[str, Any]]) -> None:
        self.tree.delete(*self.tree.get_children())
        if not self.current_dataset:
            return

        cols = self.current_dataset.columns
        for row in rows:
            values = [self._display_value(row.get(col)) for col in cols]
            self.tree.insert("", "end", values=values)
        self.filtered_rows = rows

    def _apply_filter(self) -> None:
        if not self.current_dataset:
            return

        query = self.search_var.get().strip().lower()
        if not query:
            matches = self.raw_rows
        else:
            field = self.current_dataset.filter_column
            matches = [
                row
                for row in self.raw_rows
                if query in self._display_value(row.get(field)).lower()
            ]

        self._render_rows(matches)
        self.status_var.set(f"{self.current_dataset.title}: {len(matches)} records shown")

    def _open_map_link(self, _event: tk.Event[tk.Misc]) -> None:
        if not self.current_dataset or not self.current_dataset.include_map_link:
            return

        selected = self.tree.selection()
        if not selected:
            return

        values = self.tree.item(selected[0], "values")
        if not values:
            return

        map_col = self.current_dataset.columns.index("open_map")
        url = values[map_col]
        if isinstance(url, str) and url.startswith("http"):
            import webbrowser

            webbrowser.open_new_tab(url)

    @staticmethod
    def _display_value(value: Any) -> str:
        return "" if value is None else str(value)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    PhillyDataApp().run()


if __name__ == "__main__":
    main()
