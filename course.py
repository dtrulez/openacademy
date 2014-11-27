from openerp.osv import osv, fields

class Course(osv.Model):
    _name = "openacademy.course"

    def copy(self, cr, uid, id, default, context=None):
        course = self.browse(cr, uid, id, context=context)
        new_name = "Copy of %s" % course.name
        others_count = self.search(cr, uid, [('name', '=like', new_name+'%')],
                                   count=True, context=context)
        if others_count > 0:
            new_name = "%s (%s)" % (new_name, others_count+1)
        default['name'] = new_name
        return super(Course, self).copy(cr, uid, id, default, context=context)

    def _get_attendee_count(self, cr, uid, ids, name, args, context=None):
        res = {}
        for course in self.browse(cr, uid, ids, context=context):
            res[course.id] = 0
            for session in course.session_ids:
                res[course.id] += len(session.attendee_ids)
        return res

    # /!\ This method is called from the session object!!
    def _get_courses_from_sessions(self, cr, uid, ids, context=None):
        sessions = self.browse(cr, uid, ids, context=context)
        # Return a list of Course ids with only one occurrence of each
        return list(set(session.course_id.id for session in sessions))

    _columns = {
        'name' : fields.char(string="Title", size=256, required=True),
        'description' : fields.text(string="Description"),

        # Functional fields
        'attendee_count': fields.function(_get_attendee_count, 
            type='integer', string="Attendee Count",
            store={
                'openacademy.session': 
                (_get_courses_from_sessions, ['attendee_ids'], 0)
            }),

        # Relational fields
        'responsible_id' : fields.many2one('res.users',
	    # 'set null' will reset responsibl_id to
	    # undefined if responsible was deleted
	    ondelete='set null', string='Responsible', select=True),
	# A one2many is the inverse link of a many2one
	'session_ids' : fields.one2many('openacademy.session', 'course_id', string='Session'),
    }

    _sql_constraints = [
        ('name_description_check',
         'CHECK(name <> description)',
         'The title of the course should be different of the description'),
        ('name_unique',
         'UNIQUE(name)',
         'The title must be unique'),
    ]
