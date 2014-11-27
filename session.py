from openerp.osv import osv, fields
from datetime import datetime, timedelta

class Session(osv.Model):
    _name = "openacademy.session"

    def action_draft(self, cr, uid, ids, context=None):
        #set to "draft" state
        return self.write(cr, uid, ids, {'state':'draft'}, context=context)

    def action_confirm(self, cr, uid, ids, context=None):
        #set to "confirmed" state
        return self.write(cr, uid, ids, {'state':'confirmed'}, context=context)

    def action_done(self, cr, uid, ids, context=None):
        #set to "done" state
        return self.write(cr, uid, ids, {'state':'done'}, context=context)

    def _check_instructor_not_in_attendees(self, cr, uid, ids, context=None): 
        for session in self.browse(cr, uid, ids, context):
            partners = [att.partner_id for att in session.attendee_ids] 

            if session.instructor_id and session.instructor_id in partners: 
                return False
        return True

    def _get_taken_seats_percent(self, seats, attendee_list):
        # Prevent divison-by-zero error
        try:
            # You need at least one float number to get the real value
            return (100.0 * len(attendee_list)) / seats
        except ZeroDivisionError:
            return 0.0

    # The following definition must appear *after* _get_taken_seats_percent
    # because it's called during the process
    def _taken_seats_percent(self, cr, uid, ids, field, arg, context=None):
        # Compute the percentage of seats that are booked
        result = {}
        for session in self.browse(cr, uid, ids, context=context):
            result[session.id] = self._get_taken_seats_percent(
                session.seats, session.attendee_ids)
        return result

    # Same as the previous definition: it needs to be declared
    # *after* _get_taken_seats_percent
    def onchange_taken_seats(self, cr, uid, ids, seats, attendee_ids):
        # Serializes o2m commands into record dictionaries (as if all the o2m 
        # records came from the database via a read()), and returns an
        # iterable over these dictionaries.
        attendee_records = self.resolve_2many_commands(
            cr, uid, 'attendee_ids', attendee_ids, ['id'])
        res = {
            'value' : {
                'taken_seats_percent' :
                    self._get_taken_seats_percent(seats, attendee_records),
            }
        }
        if seats < 0: res['warning'] = {
            'title'   : "Warning: bad value",
            'message' : "You cannot have negative number of seats",
        }
        elif seats < len(attendee_ids): 
            res['warning'] = {
                'title'   : "Warning: problems",
                'message' : "You need more seats for this session",
            }
        return res

    def _determin_end_date(self, cr, uid, ids, field, arg, context=None):
        result = {}
        for session in self.browse(cr, uid, ids, context=context):
            if session.start_date and session.duration:
                # Get a datetime object from session.start_date
                start_date = datetime.strptime(session.start_date, "%Y-%m-%d")
                # Get a timedelta object from session.duration
                duration = timedelta(days=(session.duration - 1))
                # Calculate the end time
                end_date = start_date + duration
                # Render in format YYYY-MM-DD
                result[session.id] = end_date.strftime("%Y-%m-%d")
            else:
                result[session.id] = session.start_date
        return result

    # Beware that fnct_inv take a unique id and not a list of id
    def _set_end_date(self, cr, uid, id, field, value, arg, context=None):
        session = self.browse(cr, uid, id, context=context)
        if session.start_date and value:
            start_date = datetime.strptime(session.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(value[:10], "%Y-%m-%d")
            duration = end_date - start_date
            self.write(cr, uid, id, {'duration' : (duration.days + 1)}, context=context)
    
    def _determin_hours_from_duration(self, cr, uid, ids, field, arg, context=None):
        result = {}
        sessions = self.browse(cr, uid, ids, context=context)
        for session in sessions:
            result[session.id] = (session.duration * 24 if session.duration else 0)
        return result

    def _set_hours(self, cr, uid, id, field, value, arg, context=None):
        if value:
            self.write(cr, uid, id, {'duration' : (value / 24)}, context=context)

    def _get_attendee_count(self, cr, uid, ids, name, args, context=None): 
        res = {}
        for session in self.browse(cr, uid, ids, context=context): 
            res[session.id] = len(session.attendee_ids)
        return res

    _columns = {
        'name' : fields.char(string="Name", size=256, required=True),
        'start_date' : fields.date(string="Start date"),
        'duration' : fields.float(string="Duration", digits=(6,2), help="Duration in days"),
        'seats' : fields.integer(string="Number of seats"),
        # Is the record active in OpenERP? (visible)
        'active' : fields.boolean("Active"),
        'color' : fields.integer('Color'),
        'state' : fields.selection([('draft','Draft'),
                                    ('confirmed','Confirmed'),
                                    ('done','Done')], string="State"),

        # Function fields are calculated on-the-fly when reading records
        'taken_seats_percent' : fields.function(_taken_seats_percent,
            type='float', string='Taken Seats'),
        'attendee_count': fields.function(_get_attendee_count,
            type='integer', string='Attendee Count', store=True),
        'end_date': fields.function(_determin_end_date,
            fnct_inv=_set_end_date, type='date', string="End Date"),
        'hours' : fields.function(_determin_hours_from_duration,
            fnct_inv=_set_hours, type='float', string="Hours"),

        # Relational fields
	'instructor_id' : fields.many2one('res.partner', string="Instructor", domain=['|', ('instructor','=',True), ('category_id.name','ilike','Teacher')]),
	'course_id' : fields.many2one('openacademy.course',
	    # 'cascade' will destroy session if course_id was deleted
	    ondelete='cascade', string="Course", required=True),
	'attendee_ids' : fields.one2many('openacademy.attendee', 'session_id', string="Attendees"),
    }

    _defaults = {
        # You can give a function or a lambda for default value. OpenERP will
        # automatically call it and get its return value at each record
        # creation. 'today' is a method of the object 'date' of module 'fields'
        # that returns -in the right timezone- the current date in the OpenERP
        # format
        'start_date' : fields.date.today,
        # Beware that is not the same as:
        # 'start_date' : fields.date.today(),
        # which actually call the method at OpenERP startup!
        'active' : True,
        'state' : 'draft',
    }

    _constraints = [
        (_check_instructor_not_in_attendees,
         "The instructor can not be also an attendee!",
         ['instructor_id','attendee_ids']),
        ]
