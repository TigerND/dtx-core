# $Id: TimedeltaField.py 638 2009-10-09 13:06:17Z tguettler $
# $HeadURL: svn+ssh://svnserver/svn/djangotools/trunk/dbfields/TimedeltaField.py $

# http://www.djangosnippets.org/snippets/1060/

# Python
import datetime

# Django
from django import forms
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

SECS_PER_DAY=3600*24

#south migration patch
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^util\.snippets\.TimedeltaField\.TimedeltaField"])
except ImportError:
    pass
#end of south migration patch


class TimedeltaField(models.Field):
    u'''
    Store Python's datetime.timedelta in an integer column.
    Most databasesystems only support 32 Bit integers by default.
    '''
    __metaclass__=models.SubfieldBase
    def __init__(self, *args, **kwargs):
        super(TimedeltaField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if (value is None) or str(value) == '':
            return None
        if isinstance(value, datetime.timedelta):
            return value
        if not isinstance(value, (int, long)):
            value = 0
            try:
                value = long(value)
            except:
                pass
        return datetime.timedelta(seconds=value)

    def get_internal_type(self):
        return 'IntegerField'

    def get_db_prep_lookup(self, lookup_type, value):
        raise NotImplementedError()  # SQL WHERE

    def get_db_prep_save(self, value):
        if (value is None) or isinstance(value, (int, long)):
            return value
        return SECS_PER_DAY*value.days+value.seconds

    def formfield(self, *args, **kwargs):
        defaults={'form_class': TimedeltaFormField}
        defaults.update(kwargs)
        return super(TimedeltaField, self).formfield(*args, **defaults)

class TimedeltaFormField(forms.Field):
    default_error_messages = {
        'invalid':  _(u'Enter a whole number.'),
        }

    def __init__(self, *args, **kwargs):
        defaults={'widget': TimedeltaWidget}
        defaults.update(kwargs)
        super(TimedeltaFormField, self).__init__(*args, **defaults)

    def clean(self, value):
        # value comes from Timedelta.Widget.value_from_datadict(): tuple of strings
        super(TimedeltaFormField, self).clean(value)
        assert len(value)==len(self.widget.inputs), (value, self.widget.inputs)
        i=0
        for value, multiply in zip(value, self.widget.multiply):
            try:
                i+=int(value)*multiply
            except ValueError, TypeError:
                raise forms.ValidationError(self.error_messages['invalid'])
        return i

    def to_python(self, value):
        if (value is None) or str(value) == '':
            return None
        if isinstance(value, datetime.timedelta):
            return value
        if isinstance(value, (tuple, list) ):
            assert len(value)==len(self.widget.inputs), (value, self.widget.inputs)
            i=0
            for value, multiply in zip(value, self.widget.multiply):
                try:
                    i+=int(value)*multiply
                except ValueError, TypeError:
                    pass
            return datetime.timedelta( 0,i )
        if isinstance(value, dict ):
            return datetime.timedelta(**value)
        if not isinstance(value, (int, long)):
            value = 0
            try:
                value = long(value)
            except:
                pass
        return datetime.timedelta(seconds=value)

class TimedeltaWidget(forms.Widget):
    INPUTS=['days', 'hours', 'minutes', 'seconds']
    INPUTNAMES=[_('Days:'), _('Hours:'), _('Minutes:'), _('Seconds:')]
    MULTIPLY=[60*60*24, 60*60, 60, 1]
    def __init__(self, attrs=None):
        self.widgets=[]
        if not attrs:
            attrs={}
        inputs=attrs.get('inputs', self.INPUTS)
        inputnames=attrs.get('inputnames', self.INPUTNAMES)
        multiply=[]
        for input in inputs:
            assert input in self.INPUTS, (input, self.INPUT)
            final_attrs = {'class':'timedelta_'+input}
            final_attrs.update(attrs)
            self.widgets.append(forms.TextInput(attrs=final_attrs))
            multiply.append(self.MULTIPLY[self.INPUTS.index(input)])
        self.inputs=inputs
        self.inputnames=inputnames
        self.multiply=multiply
        super(TimedeltaWidget, self).__init__(attrs)

    def render(self, name, value, attrs):
        if value is None:
            values=[0 for i in self.inputs]
        elif isinstance(value, datetime.timedelta):
            values=split_seconds(value.days*SECS_PER_DAY+value.seconds, self.inputs, self.multiply)
        elif isinstance(value, (int, long)):
            # initial data from model
            values=split_seconds(value, self.inputs, self.multiply)
        else:
            assert isinstance(value, tuple), (value, type(value))
            assert len(value)==len(self.inputs), (value, self.inputs)
            values=value
        id=attrs.pop('id')
        assert not attrs, attrs
        rendered=[]
        for input, inputname, widget, val in zip(self.inputs, self.inputnames, self.widgets, values):
            rendered.append(u'%s %s' % (inputname, widget.render('%s_%s' % (name, input), val)))
        return mark_safe('<p class="timedelta" id="%s">%s</p>' % (id, ' '.join(rendered)))

    def value_from_datadict(self, data, files, name):
        # Don't throw ValidationError here, just return a tuple of strings.
        ret=[]
        for input, multi in zip(self.inputs, self.multiply):
            ret.append(data.get('%s_%s' % (name, input), 0))
        return tuple(ret)

    def _has_changed(self, initial_value, data_value):
        # data_value comes from value_from_datadict(): A tuple of strings.
        if initial_value is None:
            initial_value = datetime.timedelta(0)
        print "HAS CHANGED:",initial_value, data_value
        assert isinstance(initial_value, datetime.timedelta), initial_value
        initial=tuple([unicode(i) for i in split_seconds(initial_value.days*SECS_PER_DAY+initial_value.seconds, self.inputs, self.multiply)])
        assert len(initial)==len(data_value)
        #assert False, (initial, data_value)
        return bool(initial!=data_value)

def main():
    assert split_seconds(1000000)==[11, 13, 46, 40]

    field=TimedeltaField()

    td=datetime.timedelta(days=10, seconds=11)
    s=field.get_db_prep_save(td)
    assert isinstance(s, (int, long)), (s, type(s))
    td_again=field.to_python(s)
    assert td==td_again, (td, td_again)

    td=datetime.timedelta(seconds=11)
    s=field.get_db_prep_save(td)
    td_again=field.to_python(s)
    assert td==td_again, (td, td_again)

    field=TimedeltaFormField()
    assert field.widget._has_changed(datetime.timedelta(seconds=0), (u'0', u'0', u'0', u'0',)) is False
    assert field.widget._has_changed(datetime.timedelta(days=1, hours=2, minutes=3, seconds=4), (u'1', u'2', u'3', u'4',)) is False

    print "unittest OK"

def split_seconds(secs, inputs=TimedeltaWidget.INPUTS, multiply=TimedeltaWidget.MULTIPLY):
    ret=[]
    for input, multi in zip(inputs, multiply):
        count, secs = divmod(secs, multi)
        ret.append(count)
    return ret

if __name__=='__main__':
    main()
