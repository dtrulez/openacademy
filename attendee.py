from openerp.osv import osv, fields

class Attendee(osv.Model):
    _name = "openacademy.attendee"

    # _rec_name redefines the field to get when seeing the record in
    # another object. In this case, the partner's name will be printed
    _rec_name = 'partner_id'
    # (useful when no field 'name' has been redefined)

    _columns = {
	# There is only relational fields
	'partner_id' : fields.many2one('res.partner', string="Partner",
	    required=True, ondelete='cascade'),

	'session_id' : fields.many2one('openacademy.session', string="Session",
	    required=True, ondelete='cascade'),
    }

    _sql_constraints = [
        ('partner_session_unique',
         'UNIQUE(partner_id, session_id)',
         'You can not insert the same attendee multiple times!'),
    ]
