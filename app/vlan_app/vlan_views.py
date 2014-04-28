from vlan_models import Site, Switch, Vlan, Port, Portgroup, Vlangroup, get_switches, get_vlans
from app import main, AdminModelView

from flask import render_template, flash
from flask.ext import admin, wtf, login
from flask.ext.admin.contrib import sqlamodel
from flask.ext.admin.contrib.sqlamodel import filters
from flask.ext.admin.actions import action

from operator import attrgetter

class Overview(admin.base.BaseView):
    @admin.base.expose('/')
    def index(self):
        users = main.User.query.order_by('user.username').all()
        data = []
        for i in users:
            row = {}
            row['user'] = i.username
            
            ports = main.db.session.query(Port).filter(Port.assigned_to.any(main.User.username==row['user'])).all();
            portgrp = main.db.session.query(Portgroup).filter(Portgroup.assigned_to.any(main.User.username==row['user'])).all()
    
            # go thru each group and extract ports, using set get rid of duplicates
            temp_ports = []
            for i in portgrp:
                temp_ports += set(i.ports)

            ports = set(temp_ports + ports)
            
            # filter out ports with no switch to prevent the lookup failure.
            ports = filter(lambda port: port.switch is not None, ports)
            
            try:
              sorted_ports = sorted(ports, key=attrgetter('switch.name', 'name', 'number'))
              ports_str = ", ".join(map(lambda port: str(port.switch.name) + ": " + str(port.name), sorted_ports))
            except AttributeError, e:
              ports_str = ", ".join(map(lambda port: str(port.switch.name) + ": " + str(port.name), ports))

            vlans = main.db.session.query(Vlan).filter(Vlan.assigned_to.any(main.User.username==row['user'])).all();
            vlangrp = main.db.session.query(Vlangroup).filter(Vlangroup.assigned_to.any(main.User.username==row['user'])).all()

            temp_vlans = []
            for i in vlangrp:
              temp_vlans += set(i.vlans)

            vlans = set(vlans + temp_vlans)
            vlans = sorted(vlans, key=lambda v: v.number)

            vlans_str = ", ".join(map(lambda vlan: str(vlan.number) + ": " + str(vlan.name) , vlans))

            row['ports'] = ports_str
            row['vlans'] = vlans_str
            data.append(row)

        return render_template("admin/vlan/overview.html", admin_view=self, data=data)

class BatchPorts(admin.base.BaseView):
    @admin.base.expose('/')
    def index(self):
        users = main.User.query.all()
        switches = get_switches()

        return render_template("admin/vlan/batch_ports.html", admin_view=self, data=[], switches=switches, users=users)

class BatchVlans(admin.base.BaseView):
    @admin.base.expose('/')
    def index(self):
        users = main.User.query.all()
        vlans = get_vlans()

        return render_template("admin/vlan/batch_vlans.html", admin_view=self, data=[], vlans=vlans, users=users)

class SiteAdminView(AdminModelView):
    searchable_columns = ('name', Site.name)

class PortAdminView(AdminModelView):
    searchable_columns = ('name', Port.name)
    column_filters = ('name', 'number', 'switch', Port.switch)

    @admin.base.expose('/')
    def index_view(self):
        """
            List view
        """
        def get_users(row):
            return ", ".join(map(lambda user: user.username, row.assigned_to))

        new_cols = []
        new_cols.extend(self._list_columns)
        new_cols.append(('users', 'Users'))

        self.list_template = "admin/vlan/list_with_user.html"

        # Grab parameters from URL
        page, sort_idx, sort_desc, search, filters = self._get_extra_args()

        # Map column index to column name
        sort_column = self._get_column_by_idx(sort_idx)
        if sort_column is not None:
            sort_column = sort_column[0]

        # Get count and data
        count, data = self.get_list(page, sort_column, sort_desc,
                                    search, filters)

        # Calculate number of pages
        num_pages = count / self.page_size
        if count % self.page_size != 0:
            num_pages += 1

        # Pregenerate filters
        if self._filters:
            filters_data = dict()

            for idx, f in enumerate(self._filters):
                flt_data = f.get_options(self)

                if flt_data:
                    filters_data[idx] = flt_data
        else:
            filters_data = None

        # Various URL generation helpers
        def pager_url(p):
            # Do not add page number if it is first page
            if p == 0:
                p = None

            return self._get_url('.index_view', p, sort_idx, sort_desc,
                                 search, filters)

        def sort_url(column, invert=False):
            desc = None

            if invert and not sort_desc:
                desc = 1

            return self._get_url('.index_view', page, column, desc,
                                 search, filters)

        # Actions
        actions, actions_confirmation = self.get_actions_list()

        return self.render(self.list_template,
                               data=data,
                               get_users=get_users,
                               # List
                               list_columns=new_cols,
                               sortable_columns=self._sortable_columns,
                               # Stuff
                               enumerate=enumerate,
                               get_pk_value=self.get_pk_value,
                               get_value=self.get_list_value,
                               return_url=self._get_url('.index_view',
                                                        page,
                                                        sort_idx,
                                                        sort_desc,
                                                        search,
                                                        filters),
                               # Pagination
                               count=count,
                               pager_url=pager_url,
                               num_pages=num_pages,
                               page=page,
                               # Sorting
                               sort_column=sort_idx,
                               sort_desc=sort_desc,
                               sort_url=sort_url,
                               # Search
                               search_supported=self._search_supported,
                               clear_search_url=self._get_url('.index_view',
                                                              None,
                                                              sort_idx,
                                                              sort_desc),
                               search=search,
                               # Filters
                               filters=self._filters,
                               filter_groups=self._filter_groups,
                               filter_types=self._filter_types,
                               filter_data=filters_data,
                               active_filters=filters,

                               # Actions
                               actions=actions,
                               actions_confirmation=actions_confirmation
                               )

class SwitchAdminView(AdminModelView):
    searchable_columns = ('name', Switch.name, 'vlan_oid', Switch.vlan_oid, 'interface_oid', Switch.interface_oid, 'host_address', Switch.host_address)
    column_filters = ('site', Switch.site)

    @action('update_ports', 'Update Ports', 'Are you sure you want to update ports?')
    def action_update_ports(self, ids):
        try:
            query = Switch.query.filter(Switch.id.in_(ids))

            for m in query.all():
                print m.updatePorts();

            flash('Update ports successful.')
        except Exception, ex:
            flash('Failed to update ports.' + str(ex))

# class PortAdminView(AdminModelView):
#     searchable_columns = ('name', Port.name)
#     column_filters = ('name', 'number', 'switch', Port.switch)

class VlanAdminView(AdminModelView):
    searchable_columns = ('name', Vlan.name)
    column_filters = ('name', 'number')

    @admin.base.expose('/')
    def index_view(self):
        """
            List view
        """
        def get_users(row):
            return ", ".join(map(lambda user: user.username, row.assigned_to))

        new_cols = []
        new_cols.extend(self._list_columns)
        new_cols.append(('users', 'Users'))

        self.list_template = "admin/vlan/list_with_user.html"

        # Grab parameters from URL
        page, sort_idx, sort_desc, search, filters = self._get_extra_args()

        # Map column index to column name
        sort_column = self._get_column_by_idx(sort_idx)
        if sort_column is not None:
            sort_column = sort_column[0]

        # Get count and data
        count, data = self.get_list(page, sort_column, sort_desc,
                                    search, filters)

        # Calculate number of pages
        num_pages = count / self.page_size
        if count % self.page_size != 0:
            num_pages += 1

        # Pregenerate filters
        if self._filters:
            filters_data = dict()

            for idx, f in enumerate(self._filters):
                flt_data = f.get_options(self)

                if flt_data:
                    filters_data[idx] = flt_data
        else:
            filters_data = None

        # Various URL generation helpers
        def pager_url(p):
            # Do not add page number if it is first page
            if p == 0:
                p = None

            return self._get_url('.index_view', p, sort_idx, sort_desc,
                                 search, filters)

        def sort_url(column, invert=False):
            desc = None

            if invert and not sort_desc:
                desc = 1

            return self._get_url('.index_view', page, column, desc,
                                 search, filters)

        # Actions
        actions, actions_confirmation = self.get_actions_list()

        return self.render(self.list_template,
                               data=data,
                               get_users=get_users,
                               # List
                               list_columns=new_cols,
                               sortable_columns=self._sortable_columns,
                               # Stuff
                               enumerate=enumerate,
                               get_pk_value=self.get_pk_value,
                               get_value=self.get_list_value,
                               return_url=self._get_url('.index_view',
                                                        page,
                                                        sort_idx,
                                                        sort_desc,
                                                        search,
                                                        filters),
                               # Pagination
                               count=count,
                               pager_url=pager_url,
                               num_pages=num_pages,
                               page=page,
                               # Sorting
                               sort_column=sort_idx,
                               sort_desc=sort_desc,
                               sort_url=sort_url,
                               # Search
                               search_supported=self._search_supported,
                               clear_search_url=self._get_url('.index_view',
                                                              None,
                                                              sort_idx,
                                                              sort_desc),
                               search=search,
                               # Filters
                               filters=self._filters,
                               filter_groups=self._filter_groups,
                               filter_types=self._filter_types,
                               filter_data=filters_data,
                               active_filters=filters,

                               # Actions
                               actions=actions,
                               actions_confirmation=actions_confirmation
                               )

# Add views to main admin page
main.admin.add_view(Overview(name="Overview", category="VLAN"))
main.admin.add_view(BatchPorts(name="Assign Ports - Batch", category="VLAN"))
main.admin.add_view(BatchVlans(name="Assign Vlans - Batch", category="VLAN"))
main.admin.add_view(SiteAdminView(Site, main.db.session, category="VLAN"))
main.admin.add_view(SwitchAdminView(Switch, main.db.session, category="VLAN"))
main.admin.add_view(PortAdminView(Port, main.db.session, category="VLAN"))
main.admin.add_view(VlanAdminView(Vlan, main.db.session, category="VLAN"))
main.admin.add_view(AdminModelView(Portgroup, main.db.session, name="Port Groups", category="VLAN"))
main.admin.add_view(AdminModelView(Vlangroup, main.db.session, name="User Groups", category="VLAN"))
