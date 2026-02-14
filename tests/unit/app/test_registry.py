"""Unit tests for the Registry class."""

import pytest

from src.app.registry import Registry


class TestRegistryInstantiation:
    """Tests for Registry instantiation."""

    def test_instantiation(self):
        """Test creating a Registry instance."""
        registry = Registry()
        assert registry is not None

    def test_instantiation_empty(self):
        """Test that Registry starts empty."""
        registry = Registry()
        items = list(registry.items())
        assert len(items) == 0


class TestRegistryRegister:
    """Tests for Registry.register method."""

    @pytest.fixture
    def registry(self):
        """Provide a fresh Registry instance."""
        return Registry()

    def test_register_single_item(self, registry):
        """Test registering a single item."""
        registry.register("key1", "value1")
        assert registry.get("key1") == "value1"

    def test_register_multiple_items(self, registry):
        """Test registering multiple items."""
        registry.register("key1", "value1")
        registry.register("key2", "value2")
        registry.register("key3", "value3")

        assert registry.get("key1") == "value1"
        assert registry.get("key2") == "value2"
        assert registry.get("key3") == "value3"

    def test_register_with_string_values(self, registry):
        """Test registering string values."""
        registry.register("name", "John")
        assert registry.get("name") == "John"

    def test_register_with_integer_values(self, registry):
        """Test registering integer values."""
        registry.register("count", 42)
        assert registry.get("count") == 42

    def test_register_with_list_values(self, registry):
        """Test registering list values."""
        items = [1, 2, 3]
        registry.register("items", items)
        assert registry.get("items") == items

    def test_register_with_dict_values(self, registry):
        """Test registering dictionary values."""
        data = {"key": "value", "number": 123}
        registry.register("data", data)
        assert registry.get("data") == data

    def test_register_with_object_values(self, registry):
        """Test registering object instances."""

        class CustomClass:
            def __init__(self, value):
                self.value = value

        obj = CustomClass(42)
        registry.register("object", obj)
        assert registry.get("object") is obj

    def test_register_with_none_value(self, registry):
        """Test registering None as a value."""
        registry.register("none_key", None)
        assert registry.get("none_key") is None

    def test_register_with_empty_string_key(self, registry):
        """Test registering with empty string as key."""
        registry.register("", "value")
        assert registry.get("") == "value"

    def test_register_with_special_characters_in_key(self, registry):
        """Test registering with special characters in key."""
        registry.register("key-with-dashes", "value1")
        registry.register("key_with_underscores", "value2")
        registry.register("key.with.dots", "value3")

        assert registry.get("key-with-dashes") == "value1"
        assert registry.get("key_with_underscores") == "value2"
        assert registry.get("key.with.dots") == "value3"

    def test_register_overwrites_existing_key(self, registry):
        """Test that registering with same key overwrites previous value."""
        registry.register("key", "value1")
        assert registry.get("key") == "value1"

        registry.register("key", "value2")
        assert registry.get("key") == "value2"

    def test_register_case_sensitive_keys(self, registry):
        """Test that keys are case-sensitive."""
        registry.register("Key", "value1")
        registry.register("key", "value2")
        registry.register("KEY", "value3")

        assert registry.get("Key") == "value1"
        assert registry.get("key") == "value2"
        assert registry.get("KEY") == "value3"


class TestRegistryGet:
    """Tests for Registry.get method."""

    @pytest.fixture
    def populated_registry(self):
        """Provide a Registry with some items."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", 42)
        registry.register("item3", [1, 2, 3])
        return registry

    def test_get_existing_item(self, populated_registry):
        """Test getting an existing item."""
        assert populated_registry.get("item1") == "value1"
        assert populated_registry.get("item2") == 42
        assert populated_registry.get("item3") == [1, 2, 3]

    def test_get_non_existing_item_returns_none(self, populated_registry):
        """Test that getting non-existent item returns None."""
        assert populated_registry.get("non_existent") is None

    def test_get_after_unregister(self, populated_registry):
        """Test getting after unregistering an item."""
        populated_registry.unregister("item1")
        assert populated_registry.get("item1") is None

    def test_get_with_none_value(self):
        """Test getting an item with None value."""
        registry = Registry()
        registry.register("none_item", None)
        assert registry.get("none_item") is None

    def test_get_empty_registry_returns_none(self):
        """Test getting from empty registry returns None."""
        registry = Registry()
        assert registry.get("any_key") is None

    def test_get_is_idempotent(self, populated_registry):
        """Test that multiple gets return the same value."""
        value1 = populated_registry.get("item1")
        value2 = populated_registry.get("item1")
        value3 = populated_registry.get("item1")

        assert value1 == value2 == value3 == "value1"


class TestRegistryUnregister:
    """Tests for Registry.unregister method."""

    @pytest.fixture
    def populated_registry(self):
        """Provide a Registry with some items."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")
        registry.register("item3", "value3")
        return registry

    def test_unregister_existing_item(self, populated_registry):
        """Test unregistering an existing item."""
        populated_registry.unregister("item1")
        assert populated_registry.get("item1") is None

    def test_unregister_makes_item_inaccessible(self, populated_registry):
        """Test that unregistered item becomes inaccessible."""
        assert populated_registry.get("item2") == "value2"
        populated_registry.unregister("item2")
        assert populated_registry.get("item2") is None

    def test_unregister_non_existing_item(self, populated_registry):
        """Test unregistering non-existent item doesn't raise error."""
        populated_registry.unregister("non_existent")  # Should not raise

    def test_unregister_from_empty_registry(self):
        """Test unregistering from empty registry doesn't raise error."""
        registry = Registry()
        registry.unregister("any_key")  # Should not raise

    def test_unregister_leaves_other_items_intact(self, populated_registry):
        """Test that unregistering one item leaves others intact."""
        populated_registry.unregister("item2")

        assert populated_registry.get("item1") == "value1"
        assert populated_registry.get("item2") is None
        assert populated_registry.get("item3") == "value3"

    def test_unregister_multiple_items(self, populated_registry):
        """Test unregistering multiple items."""
        populated_registry.unregister("item1")
        populated_registry.unregister("item2")

        assert populated_registry.get("item1") is None
        assert populated_registry.get("item2") is None
        assert populated_registry.get("item3") == "value3"

    def test_unregister_twice(self, populated_registry):
        """Test unregistering the same item twice."""
        populated_registry.unregister("item1")
        populated_registry.unregister("item1")  # Second unregister should be safe

        assert populated_registry.get("item1") is None

    def test_re_register_after_unregister(self, populated_registry):
        """Test re-registering an item after unregistering it."""
        populated_registry.unregister("item1")
        populated_registry.register("item1", "new_value")

        assert populated_registry.get("item1") == "new_value"


class TestRegistryClear:
    """Tests for Registry.clear method."""

    def test_clear_empty_registry(self):
        """Test clearing an empty registry."""
        registry = Registry()
        registry.clear()  # Should not raise

        assert registry.get("any_key") is None

    def test_clear_removes_all_items(self):
        """Test that clear removes all items."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")
        registry.register("item3", "value3")

        registry.clear()

        assert registry.get("item1") is None
        assert registry.get("item2") is None
        assert registry.get("item3") is None

    def test_clear_then_register(self):
        """Test that we can register after clearing."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.clear()
        registry.register("item2", "value2")

        assert registry.get("item1") is None
        assert registry.get("item2") == "value2"

    def test_clear_items_count_to_zero(self):
        """Test that items count becomes zero after clear."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        registry.clear()
        items = list(registry.items())

        assert len(items) == 0

    def test_multiple_clears(self):
        """Test multiple clear operations."""
        registry = Registry()
        registry.register("item1", "value1")

        registry.clear()
        registry.clear()
        registry.clear()

        assert registry.get("item1") is None


class TestRegistryItems:
    """Tests for Registry.items method."""

    def test_items_empty_registry(self):
        """Test items from empty registry."""
        registry = Registry()
        items = list(registry.items())

        assert len(items) == 0

    def test_items_returns_generator(self):
        """Test that items returns a generator."""
        registry = Registry()
        registry.register("item1", "value1")

        items = registry.items()
        from collections.abc import Generator

        assert isinstance(items, Generator)

    def test_items_single_item(self):
        """Test items with single registered item."""
        registry = Registry()
        registry.register("item1", "value1")

        items = list(registry.items())

        assert len(items) == 1
        assert items[0] == ("item1", "value1")

    def test_items_multiple_items(self):
        """Test items with multiple registered items."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")
        registry.register("item3", "value3")

        items = list(registry.items())

        assert len(items) == 3
        assert ("item1", "value1") in items
        assert ("item2", "value2") in items
        assert ("item3", "value3") in items

    def test_items_contains_tuples(self):
        """Test that items are returned as (name, object) tuples."""
        registry = Registry()
        registry.register("name", "John")

        items = list(registry.items())

        assert len(items) == 1
        name, obj = items[0]
        assert name == "name"
        assert obj == "John"

    def test_items_after_unregister(self):
        """Test items after unregistering."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        registry.unregister("item1")

        items = list(registry.items())
        assert len(items) == 1
        assert items[0] == ("item2", "value2")

    def test_items_after_clear(self):
        """Test items after clear."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        registry.clear()

        items = list(registry.items())
        assert len(items) == 0

    def test_items_can_iterate_multiple_times(self):
        """Test that we can iterate items multiple times."""
        registry = Registry()
        registry.register("item1", "value1")
        registry.register("item2", "value2")

        items1 = list(registry.items())
        items2 = list(registry.items())

        assert len(items1) == len(items2) == 2

    def test_items_unpacking(self):
        """Test unpacking items."""
        registry = Registry()
        registry.register("key1", "value1")
        registry.register("key2", "value2")

        for name, obj in registry.items():
            assert isinstance(name, str)
            assert isinstance(obj, str)


class TestRegistryGeneric:
    """Tests for Registry with generic types."""

    def test_registry_with_string_values(self):
        """Test Registry with string values."""
        registry = Registry[str]()
        registry.register("greeting", "Hello")
        registry.register("farewell", "Goodbye")

        assert registry.get("greeting") == "Hello"
        assert registry.get("farewell") == "Goodbye"

    def test_registry_with_integer_values(self):
        """Test Registry with integer values."""
        registry = Registry[int]()
        registry.register("count", 42)
        registry.register("answer", 101)

        assert registry.get("count") == 42
        assert registry.get("answer") == 101

    def test_registry_with_list_values(self):
        """Test Registry with list values."""
        registry = Registry[list]()
        registry.register("numbers", [1, 2, 3])
        registry.register("letters", ["a", "b", "c"])

        assert registry.get("numbers") == [1, 2, 3]
        assert registry.get("letters") == ["a", "b", "c"]

    def test_registry_with_custom_objects(self):
        """Test Registry with custom objects."""

        class Service:
            def __init__(self, name):
                self.name = name

        registry = Registry[Service]()
        service1 = Service("Service1")
        service2 = Service("Service2")

        registry.register("service1", service1)
        registry.register("service2", service2)

        assert registry.get("service1") is service1
        s1 = registry.get("service1")
        assert s1 is not None
        assert s1.name == "Service1"
        assert registry.get("service2") is service2


class TestRegistryWorkflow:
    """Tests for typical Registry workflows."""

    def test_service_registry_workflow(self):
        """Test a typical service registry workflow."""

        class DatabaseService:
            def query(self):
                return "database result"

        class CacheService:
            def get(self):
                return "cached value"

        registry = Registry()

        db_service = DatabaseService()
        cache_service = CacheService()

        registry.register("database", db_service)
        registry.register("cache", cache_service)

        assert registry.get("database") is db_service
        assert registry.get("cache") is cache_service
        db = registry.get("database")
        assert db is not None
        assert db.query() == "database result"
        cache = registry.get("cache")
        assert cache is not None
        assert cache.get() == "cached value"

    def test_plugin_registry_workflow(self):
        """Test a typical plugin registry workflow."""
        plugins = Registry()

        plugins.register("plugin_a", {"name": "Plugin A", "version": "1.0"})
        plugins.register("plugin_b", {"name": "Plugin B", "version": "2.0"})

        all_plugins = list(plugins.items())
        assert len(all_plugins) == 2

        plugins.unregister("plugin_a")
        remaining = list(plugins.items())
        assert len(remaining) == 1

    def test_factory_registry_workflow(self):
        """Test a typical factory registry workflow."""

        def string_factory():
            return "string"

        def list_factory():
            return []

        def dict_factory():
            return {}

        registry = Registry()

        registry.register("string", string_factory)
        registry.register("list", list_factory)
        registry.register("dict", dict_factory)

        string_factory_fn = registry.get("string")
        assert string_factory_fn is not None
        assert string_factory_fn() == "string"

        list_factory_fn = registry.get("list")
        assert list_factory_fn is not None
        assert list_factory_fn() == []

        dict_factory_fn = registry.get("dict")
        assert dict_factory_fn is not None
        assert dict_factory_fn() == {}

    def test_concurrent_registration(self):
        """Test registering and retrieving in sequence."""
        registry = Registry()

        for i in range(100):
            registry.register(f"item_{i}", i)

        for i in range(100):
            assert registry.get(f"item_{i}") == i

    def test_large_registry(self):
        """Test Registry with many items."""
        registry = Registry()

        # Register many items
        for i in range(1000):
            registry.register(f"key_{i}", f"value_{i}")

        # Verify all items
        assert len(list(registry.items())) == 1000
        assert registry.get("key_500") == "value_500"

        # Clear and verify empty
        registry.clear()
        assert len(list(registry.items())) == 0


class TestRegistryEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_register_with_mutable_value(self):
        """Test registering a mutable value."""
        registry = Registry()
        mutable_list = [1, 2, 3]

        registry.register("list", mutable_list)

        retrieved = registry.get("list")
        assert retrieved is mutable_list

        # Modify the retrieved list
        assert retrieved is not None
        retrieved.append(4)
        assert registry.get("list") == [1, 2, 3, 4]

    def test_register_with_boolean_values(self):
        """Test registering boolean values."""
        registry = Registry()

        registry.register("true_key", True)
        registry.register("false_key", False)

        assert registry.get("true_key") is True
        assert registry.get("false_key") is False

    def test_register_with_zero_value(self):
        """Test registering zero as a value."""
        registry = Registry()
        registry.register("zero", 0)

        assert registry.get("zero") == 0
        assert registry.get("zero") is not None

    def test_register_with_empty_string_value(self):
        """Test registering empty string as a value."""
        registry = Registry()
        registry.register("empty", "")

        assert registry.get("empty") == ""
        assert registry.get("empty") is not None

    def test_register_with_empty_list_value(self):
        """Test registering empty list as a value."""
        registry = Registry()
        registry.register("empty_list", [])

        assert registry.get("empty_list") == []
        assert registry.get("empty_list") is not None

    def test_register_with_empty_dict_value(self):
        """Test registering empty dict as a value."""
        registry = Registry()
        registry.register("empty_dict", {})

        assert registry.get("empty_dict") == {}
        assert registry.get("empty_dict") is not None

    def test_whitespace_keys(self):
        """Test keys with whitespace."""
        registry = Registry()

        registry.register(" key with spaces ", "value1")
        registry.register("\tkey\twith\ttabs\t", "value2")

        assert registry.get(" key with spaces ") == "value1"
        assert registry.get("\tkey\twith\ttabs\t") == "value2"
