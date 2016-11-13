import clr
import os

from .config import ICO_FILEPATH, BREAKLINE
from .logger import logger
from .utils import clone_pkg_from_remote, remove_local_pkg

# Verify these are needed.
clr.AddReference('System')
clr.AddReference('System.Drawing')
clr.AddReference("System.Windows.Forms")

#  Windows Forms Elements
from System.Drawing import Point, Icon, Color
from System.Windows import Forms
from System.Windows.Forms import Application, Form
from System.Windows.Forms import DialogResult, GroupBox
from System.Windows.Forms import (DataGridView,
                                  DataGridViewButtonColumn,
                                  DataGridViewAutoSizeColumnMode,
                                  DataGridViewAutoSizeColumnsMode,
                                  FormBorderStyle,
                                  DataGridViewTextBoxColumn,
                                  DataGridViewColumnHeadersHeightSizeMode,
                                  DataGridViewRowHeadersWidthSizeMode,
                                  DockStyle,
                                  BorderStyle,
                                  FormStartPosition
                                  # DataGridViewCellEventHandler,
                                  )

# http://www.ironpython.info/index.php?title=DataGridView_Custom_Formatting
# No idea why you need this, but makes data grid button listener work.
INDEXERROR = -1

class PackageManagerForm(Form):

    def __init__(self, packages, headers):
        self.packages = packages

        #  Window Settings
        self.Text = 'pyrevit - Package Manager'
        self.Icon = Icon(ICO_FILEPATH)
        self.MinimizeBox = False
        self.MaximizeBox = False
        self.BackgroundColor = Color.White
        self.FormBorderStyle = FormBorderStyle.FixedSingle
        self.StartPosition = FormStartPosition.CenterScreen
        #  Data Grid - DG
        dg = DataGridView()
        dg.Location = Point(0,0)
        dg.AllowUserToAddRows = False
        dg.AllowUserToResizeColumns = False
        dg.AllowUserToResizeRows = False
        dg.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.DisableResizing

        #  Bind Click to event
        dg.CellMouseUp += self.dg_click

        # DG Settings
        dg.RowHeadersVisible = False
        dg.AutoSize = True
        dg.BorderStyle = BorderStyle.None
        dg.BackgroundColor = Color.White
        dg.GridColor = Color.Gray
        dg.Dock = DockStyle.None
        # dg.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.AutoSize
        # dg.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill

        # Create Columns + Headers
        cols_width = 0
        for n, header in enumerate(headers):
            if not header:
                col = DataGridViewButtonColumn()
                col.Width = 100
            else:
                col = DataGridViewTextBoxColumn()
                # col.AutoSizeMode = DataGridViewAutoSizeColumnMode.AllCells
                if header == 'Description':
                    col.Width = 250

            dg.Columns.Add(col)
            dg.Columns[n].Name = header
            cols_width += col.Width



        # Create Rows + Cells
        rows_height = 0
        for n, package in enumerate(packages):
            dg.Rows.Add()
            row = dg.Rows[n]

            name = package['name']
            repo_ref = package['repo_ref']
            local_ref = package['local_ref']
            description = package['description']

            # Default Labels
            action_button = 'Install'
            remove_button = 'Uninstall'

            # Latest is Installed
            latest_installed = repo_ref == local_ref
            if latest_installed:
                action_button = '-'

            if local_ref and not latest_installed:
                action_button = 'Update'

            # Package is not installed so it cannot be removed.
            if not local_ref:
                remove_button = '-'

            # Remote Ref not found
            if not repo_ref:
                action_button = '-'

            row.Height = 30
            rows_height += row.Height
            cell_values = [name, repo_ref, local_ref, description,
                           action_button, remove_button]

            for n, cell in enumerate(row.Cells):
                cell.Value = cell_values[n]
                cell.ReadOnly = True

        #  Adjust DG Settings after content creating
        self.Width = cols_width + 18
        self.Height = rows_height + 62

        self.Controls.Add(dg)
        self.dg = dg

    def dg_click(self, sender, event):
        logger.debug('DG_CLICK')
        clicked_cell = self.get_cell_by_event(event)

        #  Exits on click on non Cells
        if not clicked_cell or not isinstance(clicked_cell.Value, str):
            return
        clicked_row = clicked_cell.RowIndex
        package = self.packages[clicked_row]
        package_name = package['name']
        package_url = package['url']

        success = None
        install = 'Install' in clicked_cell.Value or 'Update' in clicked_cell.Value
        remove = 'Uninstall' in clicked_cell.Value
        if remove:
            logger.debug('Remove Called: {}'.format(package_name))
            success = remove_local_pkg(package_name)

        if install:
            logger.debug('Installed Called: {}'.format(package_name))
            success = clone_pkg_from_remote(package_name, package_url)

        if success:
            self.toggle_action(clicked_cell)

    def get_cell_by_event(self, cell):
        """ Doc.
        """
        col_index = cell.ColumnIndex
        row_index = cell.RowIndex
        if row_index > INDEXERROR and col_index > INDEXERROR:
            row = self.dg.Rows[row_index]
            cell = row.Cells[col_index]
            return cell
        else:
            return None

    def toggle_action(self, cell):
        """ Toggles Values of buttons and cells when packages added/removed"""

        row = self.dg.Rows[cell.RowIndex]
        repo_ref = row.Cells[1]
        local_ref = row.Cells[2]

        if 'Install' in cell.Value or 'Update' in cell.Value:
            local_ref.Value = repo_ref.Value
            remove_cell = row.Cells[cell.ColumnIndex + 1]
            remove_cell.Value = 'Uninstall'
        if 'Uninstall' in cell.Value:
            local_ref.Value = ''
            action_cell = row.Cells[cell.ColumnIndex - 1]
            # If a remote repo ref is not found, button should not be on.
            if repo_ref.Value:
                action_cell.Value = 'Install'

        cell.Value = '-'
