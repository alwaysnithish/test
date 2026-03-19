from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
import json

from django.views.decorators.csrf import csrf_exempt
from django.db import OperationalError, DatabaseError


# If you have blog views in this file, wrap them like this:
def home(request):
    from blog.models import BlogPost
    recent_blog_posts = BlogPost.objects.filter(
        status='published'
    ).select_related('author', 'category').order_by('-published_at')[:6]
    
    return render(request, 'home.html', {
        'recent_blog_posts': recent_blog_posts,
    })

def help(request):
    return render(request, 'help.html')

def privacypolicy(request):
    return render(request, 'pp.html')

def termsandconditions(request):
    return render(request, 'tc.html')

def about(request):
    return render(request, 'about.html')
def contact(request):
    return render(request, 'contact.html')

def age(request):
    return render(request, 'age.html')

# Add these to your views.py file



def interest_calculator(request):
    """Main interest calculator page"""
    context = {
        'page_title': 'Interest & Loan Calculator',
        'page_description': 'Calculate simple interest, compound interest with contributions, loan payments, and compare financial plans with our comprehensive calculator.'
    }
    return render(request, 'interest.html', context)


@csrf_exempt
def simple_interest_api(request):
    """API endpoint for simple interest calculation"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        principal = float(data.get('principal'))
        rate = float(data.get('rate'))
        time = float(data.get('time'))
        time_unit = data.get('time_unit', 'years')
        
        # Convert time to years
        if time_unit == 'days':
            time_in_years = time / 365
        elif time_unit == 'months':
            time_in_years = time / 12
        else:  # years
            time_in_years = time
        
        # Calculate simple interest
        interest = (principal * rate * time_in_years) / 100
        total = principal + interest
        
        return JsonResponse({
            'success': True,
            'principal': round(principal, 2),
            'interest': round(interest, 2),
            'total': round(total, 2)
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid input: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
def compound_interest_api(request):
    """API endpoint for compound interest calculation"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        principal = float(data.get('principal'))
        rate = float(data.get('rate'))
        time = float(data.get('time'))
        frequency = int(data.get('frequency'))
        contribution = float(data.get('contribution', 0))
        contribution_frequency = int(data.get('contribution_frequency', 0))
        
        total = principal
        total_contributions = 0
        periods = time * frequency
        periodic_rate = rate / 100 / frequency
        
        # Calculate contribution per compounding period
        contribution_per_period = 0
        if contribution_frequency > 0:
            contribution_per_period = contribution * (frequency / contribution_frequency)
        
        # Calculate compound interest with contributions
        for i in range(int(periods)):
            if contribution_per_period > 0:
                total_contributions += contribution_per_period
                total = (total + contribution_per_period) * (1 + periodic_rate)
            else:
                total = total * (1 + periodic_rate)
        
        interest = total - principal - total_contributions
        
        return JsonResponse({
            'success': True,
            'principal': round(principal, 2),
            'contributions': round(total_contributions, 2),
            'interest': round(interest, 2),
            'total': round(total, 2)
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid input: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
def loan_calculator_api(request):
    """API endpoint for loan calculation with amortization schedule"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        amount = float(data.get('amount'))
        rate = float(data.get('rate'))
        term = float(data.get('term'))
        frequency = int(data.get('frequency'))
        include_schedule = data.get('include_schedule', False)
        
        # Calculate loan parameters
        periods_per_year = frequency
        total_payments = int(term * periods_per_year)
        periodic_rate = (rate / 100) / periods_per_year
        
        # Calculate payment using EMI formula
        if periodic_rate == 0:
            payment = amount / total_payments
        else:
            payment = (amount * periodic_rate * pow(1 + periodic_rate, total_payments)) / \
                     (pow(1 + periodic_rate, total_payments) - 1)
        
        total_payment = payment * total_payments
        total_interest = total_payment - amount
        
        result = {
            'success': True,
            'payment': round(payment, 2),
            'total_interest': round(total_interest, 2),
            'total_cost': round(total_payment, 2)
        }
        
        # Generate amortization schedule if requested
        if include_schedule:
            schedule = []
            balance = amount
            
            for i in range(1, min(total_payments + 1, 361)):  # Limit to 360 payments for display
                interest_paid = balance * periodic_rate
                principal_paid = payment - interest_paid
                balance = max(0, balance - principal_paid)
                
                schedule.append({
                    'period': i,
                    'payment': round(payment, 2),
                    'interest': round(interest_paid, 2),
                    'principal': round(principal_paid, 2),
                    'balance': round(balance, 2)
                })
                
                if balance <= 0:
                    break
            
            result['schedule'] = schedule
        
        return JsonResponse(result)
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid input: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
def compare_plans_api(request):
    """API endpoint for comparing two financial plans"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        principal = float(data.get('principal'))
        rate1 = float(data.get('rate1'))
        rate2 = float(data.get('rate2'))
        time = float(data.get('time'))
        
        # Calculate simple interest for both plans
        interest1 = (principal * rate1 * time) / 100
        total1 = principal + interest1
        
        interest2 = (principal * rate2 * time) / 100
        total2 = principal + interest2
        
        difference = abs(total2 - total1)
        better_plan = 1 if total1 > total2 else 2
        
        return JsonResponse({
            'success': True,
            'plan1_total': round(total1, 2),
            'plan1_interest': round(interest1, 2),
            'plan2_total': round(total2, 2),
            'plan2_interest': round(interest2, 2),
            'difference': round(difference, 2),
            'better_plan': better_plan
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid input: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


from django.views.decorators.csrf import csrf_exempt


def unit(request):
    """Main unit converter page with all categories and units"""
    
    # Define all conversion categories with their units
    categories = {
        'length': {
            'name': 'Length',
            'icon': 'fa-ruler',
            'units': {
                'mm': 'Millimeter (mm)',
                'cm': 'Centimeter (cm)',
                'm': 'Meter (m)',
                'km': 'Kilometer (km)',
                'in': 'Inch (in)',
                'ft': 'Foot (ft)',
                'yd': 'Yard (yd)',
                'mi': 'Mile (mi)'
            },
            'default_from': 'mm',
            'default_to': 'm'
        },
        'area': {
            'name': 'Area',
            'icon': 'fa-vector-square',
            'units': {
                'mm2': 'mm²',
                'cm2': 'cm²',
                'm2': 'm²',
                'km2': 'km²',
                'in2': 'in²',
                'ft2': 'ft²',
                'yd2': 'yd²',
                'mi2': 'mi²',
                'ac': 'Acre',
                'ha': 'Hectare'
            },
            'default_from': 'mm2',
            'default_to': 'm2'
        },
        'volume': {
            'name': 'Volume',
            'icon': 'fa-cube',
            'units': {
                'mm3': 'mm³',
                'cm3': 'cm³',
                'ml': 'Milliliter (ml)',
                'l': 'Liter (l)',
                'm3': 'm³',
                'km3': 'km³',
                'in3': 'in³',
                'ft3': 'ft³',
                'yd3': 'yd³',
                'gal': 'Gallon (US)',
                'qt': 'Quart (US)',
                'pt': 'Pint (US)',
                'oz': 'Fluid Ounce (US)'
            },
            'default_from': 'mm3',
            'default_to': 'l'
        },
        'weight': {
            'name': 'Weight',
            'icon': 'fa-weight',
            'units': {
                'mg': 'Milligram (mg)',
                'g': 'Gram (g)',
                'kg': 'Kilogram (kg)',
                't': 'Metric Ton (t)',
                'oz': 'Ounce (oz)',
                'lb': 'Pound (lb)',
                'st': 'Stone (st)',
                'ton': 'US Ton'
            },
            'default_from': 'mg',
            'default_to': 'kg'
        },
        'temperature': {
            'name': 'Temperature',
            'icon': 'fa-temperature-high',
            'units': {
                'c': 'Celsius (°C)',
                'f': 'Fahrenheit (°F)',
                'k': 'Kelvin (K)'
            },
            'default_from': 'c',
            'default_to': 'f'
        },
        'speed': {
            'name': 'Speed',
            'icon': 'fa-tachometer-alt',
            'units': {
                'mps': 'Meters per second (m/s)',
                'kmph': 'Kilometers per hour (km/h)',
                'mph': 'Miles per hour (mph)',
                'fps': 'Feet per second (ft/s)',
                'knot': 'Knot (kn)'
            },
            'default_from': 'mps',
            'default_to': 'kmph'
        },
        'pressure': {
            'name': 'Pressure',
            'icon': 'fa-compress',
            'units': {
                'pa': 'Pascal (Pa)',
                'kpa': 'Kilopascal (kPa)',
                'bar': 'Bar',
                'atm': 'Atmosphere (atm)',
                'psi': 'PSI',
                'mmhg': 'mmHg',
                'inhg': 'inHg',
                'torr': 'Torr'
            },
            'default_from': 'pa',
            'default_to': 'kpa'
        },
        'energy': {
            'name': 'Energy',
            'icon': 'fa-bolt',
            'units': {
                'j': 'Joule (J)',
                'kj': 'Kilojoule (kJ)',
                'mj': 'Megajoule (MJ)',
                'cal': 'Calorie (cal)',
                'kcal': 'Kilocalorie (kcal)',
                'wh': 'Watt hour (Wh)',
                'kwh': 'Kilowatt hour (kWh)',
                'btu': 'BTU',
                'ftlb': 'Foot-pound (ft·lb)',
                'erg': 'Erg'
            },
            'default_from': 'j',
            'default_to': 'kj'
        },
        'power': {
            'name': 'Power',
            'icon': 'fa-plug',
            'units': {
                'w': 'Watt (W)',
                'kw': 'Kilowatt (kW)',
                'mw': 'Megawatt (MW)',
                'hp': 'Horsepower (hp)',
                'ftlbpm': 'ft·lb/min',
                'btuph': 'BTU/h'
            },
            'default_from': 'w',
            'default_to': 'kw'
        },
        'data': {
            'name': 'Data',
            'icon': 'fa-database',
            'units': {
                'b': 'Bit (b)',
                'B': 'Byte (B)',
                'KB': 'Kilobyte (KB)',
                'MB': 'Megabyte (MB)',
                'GB': 'Gigabyte (GB)',
                'TB': 'Terabyte (TB)',
                'PB': 'Petabyte (PB)'
            },
            'default_from': 'b',
            'default_to': 'B'
        },
        'angle': {
            'name': 'Angle',
            'icon': 'fa-drafting-compass',
            'units': {
                'deg': 'Degree (°)',
                'rad': 'Radian (rad)',
                'grad': 'Gradian (grad)',
                'gon': 'Gon (gon)',
                'turn': 'Turn (turn)'
            },
            'default_from': 'deg',
            'default_to': 'rad'
        }
    }
    
    context = {
        'categories': categories,
        'page_title': 'Unit Converter',
        'page_description': 'Convert between different units of measurement across 11 categories including length, weight, temperature, and more.'
    }
    
    return render(request, 'unit.html', context)


def unit_converter_api(request):
    """API endpoint for unit conversions"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        category = data.get('category')
        value = float(data.get('value'))
        from_unit = data.get('from_unit')
        to_unit = data.get('to_unit')
        
        # Conversion factors to base units
        converters = {
            'length': {
                'mm': 0.001, 'cm': 0.01, 'm': 1, 'km': 1000,
                'in': 0.0254, 'ft': 0.3048, 'yd': 0.9144, 'mi': 1609.344
            },
            'area': {
                'mm2': 0.000001, 'cm2': 0.0001, 'm2': 1, 'km2': 1000000,
                'in2': 0.00064516, 'ft2': 0.09290304, 'yd2': 0.83612736, 
                'mi2': 2589988.110336, 'ac': 4046.8564224, 'ha': 10000
            },
            'volume': {
                'mm3': 0.000001, 'cm3': 0.001, 'ml': 0.001, 'l': 1, 
                'm3': 1000, 'km3': 1e12, 'in3': 0.016387064, 
                'ft3': 28.316846592, 'yd3': 764.554857984,
                'gal': 3.785411784, 'qt': 0.946352946, 
                'pt': 0.473176473, 'oz': 0.0295735295625
            },
            'weight': {
                'mg': 0.000001, 'g': 0.001, 'kg': 1, 't': 1000,
                'oz': 0.028349523125, 'lb': 0.45359237, 
                'st': 6.35029318, 'ton': 907.18474
            },
            'speed': {
                'mps': 1, 'kmph': 0.2777777778, 'mph': 0.44704, 
                'fps': 0.3048, 'knot': 0.514444
            },
            'pressure': {
                'pa': 1, 'kpa': 1000, 'bar': 100000, 'atm': 101325,
                'psi': 6894.757, 'mmhg': 133.3224, 
                'inhg': 3386.389, 'torr': 133.3224
            },
            'energy': {
                'j': 1, 'kj': 1000, 'mj': 1000000, 'cal': 4.184, 
                'kcal': 4184, 'wh': 3600, 'kwh': 3600000, 'btu': 1055.06, 
                'ftlb': 1.3558179483314004, 'erg': 0.0000001
            },
            'power': {
                'w': 1, 'kw': 1000, 'mw': 1000000, 'hp': 745.699872,
                'ftlbpm': 0.0225969658, 'btuph': 0.29307107
            },
            'data': {
                'b': 1, 'B': 8, 'KB': 8192, 'MB': 8388608,
                'GB': 8589934592, 'TB': 8796093022208, 
                'PB': 9007199254740992
            },
            'angle': {
                'deg': 1, 'rad': 57.29577951308232, 'grad': 0.9, 
                'gon': 0.9, 'turn': 360
            }
        }
        
        # Temperature conversion (special case)
        if category == 'temperature':
            if from_unit == 'c':
                if to_unit == 'f':
                    result = (value * 9/5) + 32
                elif to_unit == 'k':
                    result = value + 273.15
                else:
                    result = value
            elif from_unit == 'f':
                if to_unit == 'c':
                    result = (value - 32) * 5/9
                elif to_unit == 'k':
                    result = (value + 459.67) * 5/9
                else:
                    result = value
            elif from_unit == 'k':
                if to_unit == 'c':
                    result = value - 273.15
                elif to_unit == 'f':
                    result = value * 9/5 - 459.67
                else:
                    result = value
        else:
            # Standard conversion: convert to base unit, then to target unit
            base_value = value * converters[category][from_unit]
            result = base_value / converters[category][to_unit]
        
        # Format result
        if abs(result) >= 10000 or (abs(result) < 0.0001 and result != 0):
            formatted_result = f"{result:.4e}"
        else:
            result = round(result, 6)
            # Remove unnecessary decimal places
            if result % 1 == 0:
                formatted_result = int(result)
            else:
                formatted_result = result
        
        return JsonResponse({
            'success': True,
            'result': formatted_result,
            'value': value,
            'from_unit': from_unit,
            'to_unit': to_unit
        })
        
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid number format'
        }, status=400)
    except KeyError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid unit or category: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

from datetime import datetime, timedelta


def time_calculator(request):
    """Main time calculator page"""
    context = {
        'page_title': 'Time Calculator',
        'page_description': 'Calculate time differences, add or subtract time, and convert between time units with our comprehensive time calculator.'
    }
    return render(request, 'time.html', context)


@csrf_exempt
def time_difference_api(request):
    """API endpoint for calculating time difference between two dates"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        
        # Parse datetime strings
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        
        # Calculate difference
        diff = end_time - start_time
        total_seconds = abs(diff.total_seconds())
        
        # Break down into components
        days = int(total_seconds // (24 * 3600))
        remaining = total_seconds % (24 * 3600)
        hours = int(remaining // 3600)
        remaining = remaining % 3600
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        # Build formatted string
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        formatted_difference = ', '.join(parts) if parts else '0 seconds'
        
        # Calculate totals in different units
        total_days = round(total_seconds / (24 * 3600), 6)
        total_hours = round(total_seconds / 3600, 6)
        total_minutes = round(total_seconds / 60, 6)
        
        return JsonResponse({
            'success': True,
            'formatted_difference': formatted_difference,
            'total_days': total_days,
            'total_hours': total_hours,
            'total_minutes': total_minutes,
            'total_seconds': round(total_seconds, 6),
            'is_negative': diff.total_seconds() < 0
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid date format: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
def time_add_subtract_api(request):
    """API endpoint for adding or subtracting time from a base time"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        base_time_str = data.get('base_time')
        operation = data.get('operation')  # 'add' or 'subtract'
        days = int(data.get('days', 0))
        hours = int(data.get('hours', 0))
        minutes = int(data.get('minutes', 0))
        seconds = int(data.get('seconds', 0))
        
        # Parse base time
        base_time = datetime.fromisoformat(base_time_str.replace('Z', '+00:00'))
        
        # Create timedelta
        delta = timedelta(
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )
        
        # Apply operation
        if operation == 'add':
            result_time = base_time + delta
        elif operation == 'subtract':
            result_time = base_time - delta
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid operation. Use "add" or "subtract".'
            }, status=400)
        
        # Format result
        formatted_result = result_time.strftime('%B %d, %Y at %I:%M:%S %p')
        iso_result = result_time.isoformat()
        
        return JsonResponse({
            'success': True,
            'result_time': formatted_result,
            'iso_time': iso_result,
            'operation': operation,
            'adjustment': f"{days}d {hours}h {minutes}m {seconds}s"
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid input: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
def time_convert_api(request):
    """API endpoint for converting between time units"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        value = float(data.get('value'))
        from_unit = data.get('from_unit')
        to_unit = data.get('to_unit')
        
        if value < 0:
            return JsonResponse({
                'success': False,
                'error': 'Value must be non-negative'
            }, status=400)
        
        # Conversion factors to seconds
        units_to_seconds = {
            'seconds': 1,
            'minutes': 60,
            'hours': 3600,
            'days': 86400,
            'weeks': 604800,
            'months': 2592000,  # Approximate: 30 days
            'years': 31536000   # 365 days
        }
        
        if from_unit not in units_to_seconds or to_unit not in units_to_seconds:
            return JsonResponse({
                'success': False,
                'error': 'Invalid time unit'
            }, status=400)
        
        # Convert to seconds, then to target unit
        value_in_seconds = value * units_to_seconds[from_unit]
        result = value_in_seconds / units_to_seconds[to_unit]
        
        # Format result
        if result >= 1000000 or (result < 0.0001 and result != 0):
            formatted_result = f"{result:.4e}"
        else:
            formatted_result = round(result, 6)
            if formatted_result % 1 == 0:
                formatted_result = int(formatted_result)
        
        return JsonResponse({
            'success': True,
            'result': formatted_result,
            'value': value,
            'from_unit': from_unit,
            'to_unit': to_unit,
            'conversion_string': f"{value} {from_unit} = {formatted_result} {to_unit}"
        })
        
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid number format'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
# Add this to your views.py file



def age_calculator(request):
    """Main age calculator page"""
    context = {
        'page_title': 'Age Calculator',
        'page_description': 'Calculate your exact age in years, months, days, hours, minutes, and seconds. Get detailed life statistics and planetary ages.'
    }
    return render(request, 'age.html', context)


@csrf_exempt
def age_calculate_api(request):
    """API endpoint for calculating age with detailed statistics"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        birth_date_str = data.get('birth_date')
        birth_time_str = data.get('birth_time', '00:00')
        target_date_str = data.get('target_date')
        target_time_str = data.get('target_time', '23:59')
        
        # Parse dates
        birth_datetime = datetime.strptime(f"{birth_date_str} {birth_time_str}", "%Y-%m-%d %H:%M")
        
        if target_date_str:
            target_datetime = datetime.strptime(f"{target_date_str} {target_time_str}", "%Y-%m-%d %H:%M")
        else:
            target_datetime = datetime.now()
        
        if birth_datetime > target_datetime:
            return JsonResponse({
                'success': False,
                'error': 'Birth date cannot be in the future'
            }, status=400)
        
        # Calculate age components
        age_data = calculate_detailed_age(birth_datetime, target_datetime)
        
        return JsonResponse({
            'success': True,
            'age_data': age_data
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid date format: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def calculate_detailed_age(birth_date, target_date):
    """Calculate detailed age statistics"""
    # Calculate time difference
    diff = target_date - birth_date
    total_seconds = diff.total_seconds()
    
    # Calculate basic units
    years = target_date.year - birth_date.year
    months = target_date.month - birth_date.month
    days = target_date.day - birth_date.day
    
    # Adjust for negative days/months
    if days < 0:
        months -= 1
        # Get last day of previous month
        if target_date.month == 1:
            last_month = 12
            last_year = target_date.year - 1
        else:
            last_month = target_date.month - 1
            last_year = target_date.year
        
        from calendar import monthrange
        days += monthrange(last_year, last_month)[1]
    
    if months < 0:
        years -= 1
        months += 12
    
    # Calculate totals
    total_days = int(total_seconds // (24 * 3600))
    total_hours = int(total_seconds // 3600)
    total_minutes = int(total_seconds // 60)
    
    # Biological estimates
    heartbeats = total_days * 100000
    breaths = total_days * 20000
    blinks = total_days * 28800
    hair_growth = total_days / 60  # 0.5 inches per month
    sleep_hours = total_days * 8
    
    # Planetary ages (orbital periods in Earth days)
    planetary_periods = {
        'Mercury': 88,
        'Venus': 225,
        'Mars': 687,
        'Jupiter': 4333,
        'Saturn': 10759,
        'Uranus': 30687,
        'Neptune': 60190,
        'Pluto': 90560
    }
    
    planetary_ages = {}
    for planet, period in planetary_periods.items():
        planetary_ages[planet] = round(total_days / period, 2)
    
    # Life statistics
    weekends = int(total_days * 2 / 7)
    meals = total_days * 3
    steps = total_days * 7500
    words = total_days * 16000
    laughs = total_days * 15
    
    # Zodiac and birth info
    zodiac_sign = get_zodiac_sign(birth_date.month, birth_date.day)
    birthstone = get_birthstone(birth_date.month)
    birth_flower = get_birth_flower(birth_date.month)
    day_of_week = birth_date.strftime('%A')
    
    # Generation
    birth_year = birth_date.year
    generation = get_generation(birth_year)
    
    return {
        'basic_age': {
            'years': years,
            'months': months,
            'days': days,
            'total_days': total_days,
            'total_hours': total_hours,
            'total_minutes': total_minutes,
            'total_seconds': int(total_seconds)
        },
        'biological': {
            'heartbeats': f"{heartbeats:,.0f}",
            'breaths': f"{breaths:,.0f}",
            'blinks': f"{blinks:,.0f}",
            'hair_growth': f"{hair_growth:.1f}",
            'sleep_hours': f"{sleep_hours:,.0f}"
        },
        'planetary_ages': planetary_ages,
        'life_stats': {
            'weekends': f"{weekends:,}",
            'meals': f"{meals:,}",
            'steps': f"{steps:,}",
            'words': f"{words:,}",
            'laughs': f"{laughs:,}"
        },
        'birth_info': {
            'zodiac_sign': zodiac_sign,
            'birthstone': birthstone,
            'birth_flower': birth_flower,
            'day_of_week': day_of_week,
            'generation': generation
        }
    }


def get_zodiac_sign(month, day):
    """Get zodiac sign based on birth month and day"""
    zodiac_dates = [
        (1, 20, "Capricorn"), (2, 19, "Aquarius"), (3, 21, "Pisces"),
        (4, 20, "Aries"), (5, 21, "Taurus"), (6, 21, "Gemini"),
        (7, 23, "Cancer"), (8, 23, "Leo"), (9, 23, "Virgo"),
        (10, 23, "Libra"), (11, 22, "Scorpio"), (12, 22, "Sagittarius"),
        (12, 31, "Capricorn")
    ]
    
    for m, d, sign in zodiac_dates:
        if month < m or (month == m and day <= d):
            return sign
    return "Capricorn"


def get_birthstone(month):
    """Get birthstone for birth month"""
    birthstones = {
        1: "Garnet", 2: "Amethyst", 3: "Aquamarine", 4: "Diamond",
        5: "Emerald", 6: "Pearl", 7: "Ruby", 8: "Peridot",
        9: "Sapphire", 10: "Opal", 11: "Topaz", 12: "Turquoise"
    }
    return birthstones.get(month, "Unknown")


def get_birth_flower(month):
    """Get birth flower for birth month"""
    flowers = {
        1: "Carnation", 2: "Violet", 3: "Daffodil", 4: "Daisy",
        5: "Lily of the Valley", 6: "Rose", 7: "Larkspur", 8: "Gladiolus",
        9: "Aster", 10: "Marigold", 11: "Chrysanthemum", 12: "Narcissus"
    }
    return flowers.get(month, "Unknown")


def get_generation(birth_year):
    """Get generation based on birth year"""
    if 1928 <= birth_year <= 1945:
        return "Silent Generation"
    elif 1946 <= birth_year <= 1964:
        return "Baby Boomer"
    elif 1965 <= birth_year <= 1980:
        return "Generation X"
    elif 1981 <= birth_year <= 1996:
        return "Millennial"
    elif 1997 <= birth_year <= 2012:
        return "Generation Z"
    elif birth_year >= 2013:
        return "Generation Alpha"
    else:
        return "Unknown"
